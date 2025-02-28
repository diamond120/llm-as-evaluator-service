from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import gevent
from gevent import Greenlet
from gevent.pool import Pool
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.formatter_to_issues import format_output_to_issues
from evaluators.library.single_stage_messages import SingleStageMessagesEvaluator


class CellFilterConfig(BaseModel):
    field_name: str = Field(..., description="Field name to filter cells by")
    field_value: Any = Field(..., description="Value to match against the field")
    filter_history: bool = Field(
        default=False,
        description="Whether to apply the same filter to history cells",
    )


class CBCTwoStageEvaluator(SingleStageMessagesEvaluator):

    class ConfigSchema(BaseModel):
        """Evaluator type config schema"""

        cbc_messages: list[tuple[str, Any]] = Field(
            ...,
            description="Messages in the format of [(role, payload), ...] to be run on each cell",
        )
        cbc_output_schema: dict = Field(
            ..., description="Output schema for the CBC evaluator"
        )
        messages: list[tuple[str, Any]] = Field(
            ...,
            description="Overall evaluation messages in the format of [(role, payload), ...]",
        )
        with_history: bool = Field(
            ..., description="Whether to include history before the cell"
        )
        history_preprocessing_messages: Optional[list[tuple[str, Any]]] = Field(
            default=None,
            description="Messages in the format of [(role, payload), ...] to be run on history before inserting if enabled",
        )
        history_preprocessing_output_schema: Optional[dict] = Field(
            default={},
            description="Output schema for the history output before inserting if enabled",
        )
        focus_on_field: Optional[str] = Field(
            default=None,
            description="If provided, we will only use the provided field from the list of items in input named `conversation`.",
        )
        cell_filter_by_field: Optional[CellFilterConfig] = Field(
            default=None,
            description="Configuration for filtering cells based on field name and value",
        )

    class CBCInputSchema(BaseModel):
        cell: Any = Field(..., description="Cell payload")
        history: Any | None = Field(default=None, description="Cell history payload")

    class HistoryPreprocessingInputSchema(BaseModel):
        history: Any | None = Field(default=None, description="Cell history payload")

    def evaluate(
        self,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        input_validation: bool = True,
        parse: bool = True,
        format_to_issues_scores: bool = False,
    ):
        logger.debug(
            "Starting evaluate function with input_data: %s, config: %s, input_validation: %s, parse: %s, format_to_issues_scores: %s, run_id: %s",
            input_data,
            config,
            input_validation,
            parse,
            format_to_issues_scores,
            self.run_id,
        )

        input_data = {**input_data, **config}
        logger.debug(
            "Merged input_data with config: %s, run_id: %s", input_data, self.run_id
        )

        self.validate_input(input_data)
        logger.debug("Input data validated, run_id: %s", self.run_id)

        cbc_messages = self.config["cbc_messages"]
        cbc_output_schema = self.config["cbc_output_schema"]
        with_history = self.config["with_history"]
        logger.debug(
            "Configuration - cbc_messages: %s, cbc_output_schema: %s, with_history: %s, run_id: %s",
            cbc_messages,
            cbc_output_schema,
            with_history,
            self.run_id,
        )

        cbc_evaluator = SingleStageMessagesEvaluator(
            "cbc_" + self.name,
            {"messages": cbc_messages, "retries": self.config.get("retries", 3)},
            self.llm_config,
            SingleStageMessagesEvaluator.ConfigSchema.model_json_schema(),
            self.CBCInputSchema.model_json_schema(),
            output_schema=cbc_output_schema,
        )
        logger.debug(
            "Initialized SingleStageMessagesEvaluator: %s, run_id: %s",
            cbc_evaluator,
            self.run_id,
        )

        results = [None] * len(input_data["conversation"])
        logger.debug(
            "Initialized results list with None: %s, run_id: %s", results, self.run_id
        )

        total_metadata = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        cell_filter = self.config.get("cell_filter_by_field")
        conversation = input_data["conversation"]

        if cell_filter:
            filtered_indices = []
            filtered_conversation = []

            for idx, cell in enumerate(conversation):
                if (
                    isinstance(cell, dict)
                    and cell.get(cell_filter["field_name"])
                    == cell_filter["field_value"]
                ):
                    filtered_indices.append(idx)
                    filtered_conversation.append(cell)

            logger.debug(
                f"Filtered conversation from {len(conversation)} to {len(filtered_conversation)} cells based on "
                f"field '{cell_filter.get('field_name')}' with value '{cell_filter.get('field_value')}', "
                f"filter_history={cell_filter.get('filter_history')}, run_id: {self.run_id}"
            )

            conversation = filtered_conversation
        else:
            filtered_indices = list(range(len(conversation)))


        def evaluate_cell(index, cell):
            if self.config.get("focus_on_field"):
                cell = cell[self.config["focus_on_field"]]
            payload = {"cell": cell}
            history_result = None
            if with_history:
                orig_index = filtered_indices[index]
                history_cells = input_data["conversation"][:orig_index]
                # Apply filtering to history only if configured
                if cell_filter and cell_filter.get("filter_history"):
                    history_cells = [
                        cell
                        for cell in history_cells
                        if isinstance(cell, dict)
                        and cell.get(cell_filter["field_name"])
                        == cell_filter["field_value"]
                    ]
                    logger.debug(
                        f"Filtered history cells for index {index}, "
                        f"filtered from {len(input_data['conversation'][:orig_index])} to {len(history_cells)} cells, "
                        f"run_id: {self.run_id}"
                    )
                payload["history"] = history_cells
                if self.config.get("history_preprocessing_messages"):
                    history_preprocessing_evaluator = SingleStageMessagesEvaluator(
                        "history_preprocessing_" + self.name,
                        {
                            "messages": self.config["history_preprocessing_messages"],
                            "retries": self.config.get("retries", 3),
                        },
                        self.llm_config,
                        SingleStageMessagesEvaluator.ConfigSchema.model_json_schema(),
                        self.HistoryPreprocessingInputSchema.model_json_schema(),
                        output_schema=self.config[
                            "history_preprocessing_output_schema"
                        ],
                    )
                    gevent.sleep(0)
                    history_result = history_preprocessing_evaluator.evaluate(
                        {**input_data, **payload},
                        config,
                        parse=parse,
                        input_validation=input_validation,
                    )
                    payload["history"] = history_result["result"]
            logger.debug(
                f"Evaluating cell {index} with payload size: {len(str(payload))}, "
                f"history size: {len(payload.get('history', []))}, run_id: {self.run_id}"
            )
            gevent.sleep(0)
            result = cbc_evaluator.evaluate(
                {**input_data, **payload},
                config,
                parse=parse,
                input_validation=input_validation,
            )
            if history_result and result:
                history_metadata = history_result.get("metadata", {})
                for key in result["metadata"]:
                    result["metadata"][key] += history_metadata.get(key, 0)
            gevent.sleep(0)
            logger.debug(
                "Result for cell %d: %s, run_id: %s", index, result, self.run_id
            )
            return index, result

        pool = Pool(10)  # Create a pool with a maximum of 10 greenlets
        logger.debug("Gevent Pool initialized with size 10, run_id: %s", self.run_id)
        greenlets = [
            pool.spawn(evaluate_cell, index, cell)
            for index, cell in enumerate(conversation)
        ]
        pool.join(raise_error=True)  # Wait for all greenlets to finish
        logger.debug(
            "Spawned greenlets for evaluation: %s, run_id: %s", greenlets, self.run_id
        )

        cbc_outputs = []
        for greenlet in greenlets:
            try:
                result_index, result = greenlet.get()
                results[result_index] = result.get("result", {})
                cbc_outputs.append(result.get("result", {}))

                # Aggregate metadata
                cell_metadata = result.get("metadata", {})
                for key in total_metadata:
                    total_metadata[key] += cell_metadata.get(key, 0)

                logger.debug(
                    "Greenlet result for index %d: %s, run_id: %s",
                    result_index,
                    result,
                    self.run_id,
                )
            except Exception as e:
                if len(greenlet.args) > 0:
                    logger.error(
                        "Error evaluating cell %d: %s, run_id: %s",
                        greenlet.args[0],
                        e,
                        self.run_id,
                        exc_info=True,
                    )
                    results[greenlet.args[0]] = None
                else:
                    logger.error(
                        "Error evaluating cell: %s, run_id: %s",
                        e,
                        self.run_id,
                        exc_info=True,
                    )
                raise e
        gevent.sleep(0)
        # results = [result for result in results if result is not None]
        logger.debug("Filtered results: %s, run_id: %s", results, self.run_id)
        if self.config["messages"]:
            stage2_result = super().evaluate(
                {**input_data, "original_input": input_data, "evaluations": results},
                config,
                input_validation=False,  # We've already validated the input
                parse=parse,
            )

            # Aggregate stage2 metadata
            stage2_metadata = stage2_result.get("metadata", {})
            for key in total_metadata:
                total_metadata[key] += stage2_metadata.get(key, 0)

            res = {
                "metadata": total_metadata,
                "result": {
                    "stage2_output": stage2_result.get("result", {}),
                    "multi_outputs": cbc_outputs,
                },
            }

        else:
            res = {"metadata": total_metadata, "result": {"multi_outputs": cbc_outputs}}

        logger.info("Evaluation results: %s, run_id: %s", res, self.run_id)

        if format_to_issues_scores:
            logger.info("Formatting output to issues scores, run_id: %s", self.run_id)
            formatted_res = format_output_to_issues(res["result"], run_id=self.run_id)
            logger.debug("Formatted output: %s, run_id: %s", formatted_res, self.run_id)
            return {"metadata": res["metadata"], "result": formatted_res}
        else:
            return res
