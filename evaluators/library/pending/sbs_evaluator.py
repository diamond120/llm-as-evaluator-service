from abc import abstractmethod
from enum import Enum
from typing import Any

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


class SideBySideEvaluator(SingleStageMessagesEvaluator):
    class ConfigSchema(BaseModel):
        """Evaluator type config schema"""

        sbs_messages: list[tuple[str, Any]] = Field(
            ...,
            description="Messages in the format of [(role, payload), ...], must include item_1, item_2, ... input params, from 1 not 0",
        )
        sbs_output_schema: dict = Field(
            ...,
            description="Output schema for the SBS evaluator if apply_reversed=True, otherwise main output schema is used.",
        )
        apply_reversed: bool = Field(
            ...,
            description="If True, the responses evaluated will be reversed in placement and the results will be provided into a separate LLM call.",
        )
        union_messages: list[tuple[str, Any]] = Field(
            ...,
            description="Overall evaluation messages in the format of [(role, payload), ...] if apply_reversed is True. must contain `evaluations` param",
        )

    class GlobalInputSchema(BaseModel):
        common_part: Any = Field(..., description="Common part that is static.")
        sbs_parts: list[Any] = Field(
            ..., description="Items to be compared side by side."
        )

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False,
    ):
        logger.debug(
            "Starting evaluate function with input_data: %s, config: %s, input_validation: %s, parse: %s, format_to_issues_scores: %s",
            input_data,
            config,
            input_validation,
            parse,
            format_to_issues_scores,
        )

        input_data = {**input_data, **config}
        logger.debug("Merged input_data with config: %s", input_data)

        self.validate_input(input_data)
        logger.debug("Input data validated.")

        sbs_messages = self.config["sbs_messages"]
        sbs_output_schema = self.config["sbs_output_schema"]
        apply_reversed = self.config["apply_reversed"]
        union_messages = self.config["union_messages"]
        logger.debug(
            "Configuration - sbs_messages: %s, sbs_output_schema: %s, apply_reversed: %s, union_messages: %s",
            sbs_messages,
            sbs_output_schema,
            apply_reversed,
            union_messages,
        )

        cbc_evaluator = SingleStageMessagesEvaluator(
            "sbs_" + self.name,
            {"messages": sbs_messages, "retries": self.config.get("retries", 3)},
            self.llm_config,
            SingleStageMessagesEvaluator.ConfigSchema.model_json_schema(),
            {},
            output_schema=sbs_output_schema if apply_reversed else self.output_schema,
        )
        logger.debug("Initialized SingleStageMessagesEvaluator: %s", cbc_evaluator)

        results = [None]
        if apply_reversed:
            results = [None, None]
        logger.debug("Initialized results list with None: %s", results)

        def evaluate_sbs_parts(index, common_part, sbs_parts):
            payload = {"common_part": common_part}
            for idx, part in enumerate(sbs_parts):
                payload[f"item_{idx + 1}"] = part
            logger.debug("Evaluating cell %d with payload: %s", index, payload)
            result = cbc_evaluator.evaluate(
                payload,
                config,
                parse=parse,
                input_validation=False,
            )
            gevent.sleep(0)
            logger.debug("Result for cell %d: %s", index, result)
            return index, result

        pool = Pool(2)  # Create a pool with a maximum of 10 greenlets
        logger.debug("Gevent Pool initialized with size 2")
        greenlets = [
            pool.spawn(
                evaluate_sbs_parts,
                0,
                input_data["common_part"],
                input_data["sbs_parts"],
            )
        ]
        if apply_reversed:
            raise NotImplementedError(
                "If we evaluate this way then reversed, llm might reference the items and it will be mixed, also issues for 1 will be issues for 3 in the second run, need improvement"
            )
            greenlets.append(
                pool.spawn(
                    evaluate_sbs_parts,
                    1,
                    input_data["common_part"],
                    input_data["sbs_parts"][::-1],
                )
            )
        pool.join()  # Wait for all greenlets to finish
        logger.debug("Spawned greenlets for evaluation: %s", greenlets)

        for greenlet in greenlets:
            try:
                result_index, result = greenlet.get()
                results[result_index] = result
                logger.debug("Greenlet result for index %d: %s", result_index, result)
            except Exception as e:
                if len(greenlet.args) > 0:
                    logger.error(
                        "Error evaluating sbs step %d: %s",
                        greenlet.args[0],
                        e,
                        exc_info=True,
                    )
                    results[greenlet.args[0]] = None
                else:
                    logger.error("Error evaluating sbs step: %s", e, exc_info=True)

        results = [result for result in results if result is not None]
        logger.debug("Filtered results: %s", results)

        if apply_reversed:
            res = {
                "stage2_output": super().evaluate(
                    {"evaluations": results},
                    config,
                    input_validation=input_validation,
                    parse=parse,
                ),
                "multi_outputs": results,
            }
        else:
            res = results[0]
        logger.info("Evaluation results: %s", res)

        if format_to_issues_scores:
            logger.info("Formatting output to issues scores")
            formatted_res = format_output_to_issues(res)
            logger.debug("Formatted output: %s", formatted_res)
            return formatted_res
        else:
            return res
