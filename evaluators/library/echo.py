import time
from abc import abstractmethod
from typing import Any, Dict, List, Tuple

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.langchain_evaluator_base import LangChainBaseEvaluator


class EchoSingleStageMessagesEvaluator(LangChainBaseEvaluator):

    class ConfigSchema(BaseModel):
        """Evaluator type config schema"""

        messages: list[tuple[str, Any]] = Field(
            ..., description="Messages in the format of [(role, payload), ...]"
        )

    def create_prompt(self, input_data: Dict[str, Any]) -> ChatPromptTemplate:
        logger.debug("Creating prompt with input data: %s", input_data)
        chat_template = ChatPromptTemplate.from_messages([("system", "message")])
        return chat_template

    def evaluate(
        self,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        input_validation: bool = True,
        parse: bool = True,
        format_to_issues_scores: bool = False,
    ) -> Dict[str, Any]:

        logger.info(
            "Starting evaluation with input_data: %s and config: %s", input_data, config
        )

        if "delay" in config and config["delay"]:
            logger.info("Delaying execution by %s seconds", config["delay"])
            time.sleep(config["delay"])

        if parse is None:
            parse = True

        input_data = {**input_data, **config}

        if input_validation:
            logger.debug("Validating input data")
            self.validate_input(input_data)

        # Simulate token usage for consistency
        simulated_metadata = {
            "total_tokens": 10,
            "prompt_tokens": 5,
            "completion_tokens": 5,
        }

        result = {
            "inputs": {
                "input_data": list(input_data.keys()),
                "config": list(config.keys()),
                "input_validation": input_validation,
                "parse": parse,
                "format_to_issues_scores": format_to_issues_scores,
            }
        }

        logger.debug("Evaluation result: %s", result)

        if parse:
            logger.info("Returning parsed result")
            return {"metadata": simulated_metadata, "result": result}
        else:
            logger.info("Returning raw output")
            return {
                "metadata": simulated_metadata,
                "result": {"RAW_OUTPUT": str(result)},
            }
