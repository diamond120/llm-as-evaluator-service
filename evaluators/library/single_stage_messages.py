from abc import abstractmethod
from typing import Any, Optional

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.langchain_evaluator_base import LangChainBaseEvaluator


class SingleStageMessagesEvaluator(LangChainBaseEvaluator):

    class ConfigSchema(BaseModel):
        """Evaluator type config schema"""

        messages: list[tuple[str, Any]] = Field(
            ..., description="Messages in the format of [(role, payload), ...]"
        )

    def create_prompt(self, input_data):
        logger.debug(
            "Creating prompt with input data: %s, run_id: %s", input_data, self.run_id
        )
        messages = self.config["messages"]
        logger.debug(
            "Loaded messages from config: %s, run_id: %s", messages, self.run_id
        )
        messages = [tuple(message) for message in messages]
        logger.debug(
            "Converted messages to tuples: %s, run_id: %s", messages, self.run_id
        )
        try:
            chat_template = ChatPromptTemplate.from_messages(messages)
            logger.info("Chat template created successfully, run_id: %s", self.run_id)
        except Exception as e:
            logger.error(
                "Failed to create chat template, run_id: %s", self.run_id, exc_info=True
            )
            raise e
        return chat_template
