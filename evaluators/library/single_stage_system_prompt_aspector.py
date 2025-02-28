from abc import abstractmethod
from enum import Enum

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.library.single_stage_system_prompt import (
    SingleStageSystemPromptEvaluator,
)


class SingleStageSystemPromptAspectorEvaluator(SingleStageSystemPromptEvaluator):

    def create_prompt(self, input_data):
        logger.debug("Creating prompt with input data: %s", input_data)
        system_prompt = self.config["system_prompt"]
        first_user_message = self.config["first_user_message"]
        if input_data["role"] not in self.config["role_map"]:
            logger.error("Invalid role: %s", input_data["role"])
            raise ValueError(
                f'Invalid role: {input_data["role"]}. Must be one of {self.config["role_map"].keys()}.'
            )
        conversation_side = self.config["role_map"][input_data["role"]]
        system_prompt += "\n" + conversation_side + "\n--------\n"

        chat_template = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt),
                HumanMessagePromptTemplate.from_template(first_user_message),
            ]
        )
        logger.info("Prompt created successfully")
        return chat_template

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=None,
        format_to_issues_scores=False,  # already in correct format
    ):
        logger.debug(
            "Evaluating with input data: %s and config: %s", input_data, config
        )
        result = super().evaluate(
            input_data,
            config,
            input_validation=input_validation,
            parse=parse,
            format_to_issues_scores=False,
        )
        logger.info("Evaluation completed successfully")
        return result
