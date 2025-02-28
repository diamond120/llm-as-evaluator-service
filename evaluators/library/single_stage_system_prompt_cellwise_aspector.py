from abc import abstractmethod
from enum import Enum
from typing import List, Dict, Any

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.library.single_stage_system_prompt import (
    SingleStageSystemPromptEvaluator,
)


class QualityAspect(BaseModel):
    name: str = Field(..., description="The name of the quality aspect.")
    instruction: str = Field(
        ..., description="Instructions & details on how to inspect this quality aspect."
    )


class InputSchema(BaseModel):
    quality_aspect: QualityAspect = Field(
        ...,
        description="The quality aspect to focus on during the evaluation, including its name and specific instructions.",
    )
    conversation_cell: dict[str, Any] = Field(
        ..., description="The conversation cell to be evaluated."
    )
    metadata: dict[str, Any] = Field(
        ..., description="Metadata related to the conversation."
    )


class SingleStageSystemPromptCellwiseAspectorEvaluator(
    SingleStageSystemPromptEvaluator
):

    def evaluate(
        self,
        input_data: Dict[str, Any],
        evaluation_config: Dict[str, Any],
        input_validation: bool = True,
        parse: bool = True,
    ) -> Dict[str, Any]:

        logger.info("Starting evaluation with input data and evaluation config.")
        input_data = {**input_data, **evaluation_config}

        logger.debug("Validating input data.")
        self.validate_input(input_data)

        logger.debug("Initializing sub evaluator.")
        sub_evaluator = SingleStageSystemPromptEvaluator(
            "sub_" + self.name,
            {
                "system_prompt": self.config["system_prompt"],
                "first_user_message": self.config["first_user_message"],
            },
            self.llm_config,
            SingleStageSystemPromptEvaluator.ConfigSchema.model_json_schema(),
            InputSchema.model_json_schema(),
            self.output_schema,
        )

        results = []
        total_metadata = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        logger.info("Starting evaluation of conversation cells.")
        for cell in input_data["conversation"]:
            logger.debug(f"Evaluating conversation cell: {cell}")
            cell_result = sub_evaluator.evaluate(
                {
                    "conversation_cell": cell,
                    "metadata": input_data["metadata"],
                    "quality_aspect": input_data["quality_aspect"],
                },
                evaluation_config,
                parse=parse,
            )
            # Extract and aggregate token usage
            cell_metadata = cell_result.get("metadata", {})
            for key in total_metadata:
                total_metadata[key] += cell_metadata.get(key, 0)

            results.append(cell_result.get("result"))

        logger.info("Evaluation completed.")
        return {"metadata": total_metadata, "results": results}
