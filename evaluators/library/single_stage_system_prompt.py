from abc import abstractmethod
from typing import Optional

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.langchain_evaluator_base import LangChainBaseEvaluator


class SingleStageSystemPromptEvaluator(LangChainBaseEvaluator):

    class ConfigSchema(BaseModel):
        """Evaluator type"""

        system_prompt: str = Field(
            ..., description="The system prompt configuration as a string."
        )
        first_user_message: Optional[str] = Field(
            None, description="The first user message in the conversation."
        )

    def create_prompt(self, input_data):
        logger.debug("Creating prompt with input data: %s", input_data)
        system_prompt = self.config["system_prompt"]
        messages = [SystemMessagePromptTemplate.from_template(system_prompt)]
        first_user_message = self.config.get("first_user_message")
        if first_user_message:
            logger.debug("Adding first user message to prompt: %s", first_user_message)
            messages.append(
                HumanMessagePromptTemplate.from_template(first_user_message)
            )

        chat_template = ChatPromptTemplate.from_messages(messages)
        logger.info("Chat prompt template created successfully")
        return chat_template

    def validata_input(self, input_data, **kwargs):
        logger.debug("Validating input data: %s", input_data)
        super().validate_input(input_data, **kwargs)
        args_list = self.config["expected_arguments"]
        missing_args = [arg for arg in args_list if arg not in input_data]
        extra_args = [arg for arg in input_data if arg not in args_list]
        if missing_args:
            logger.error("Missing argument(s): %s", ", ".join(missing_args))
            raise ValueError(f"Missing argument(s): {', '.join(missing_args)}")
        if extra_args:
            logger.error("Extra argument(s): %s", ", ".join(extra_args))
            raise ValueError(f"Extra argument(s): {', '.join(extra_args)}")
        logger.info("Input data validated successfully")
