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


class AspectorRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    ALL = "all"


class SpecificSingleStageSystemPromptAspectorEvaluator(
    SingleStageSystemPromptEvaluator
):

    def create_prompt(self, input_data):
        logger.debug("Creating prompt with input data: %s", input_data)

        system_prompt = self.config["system_prompt"]
        first_user_message = self.config.get("first_user_message")

        valid_roles = [role.value for role in AspectorRole]
        picked_role = self.config["picked_role"]
        if picked_role not in valid_roles:
            logger.error(
                "Invalid role: %s. Must be one of %s.", picked_role, valid_roles
            )
            raise ValueError(
                f"Invalid role: {picked_role}. Must be one of {valid_roles}."
            )
        logger.info("Picked role: %s", picked_role)

        conversation_side = self.config["role_map"][picked_role]
        system_prompt += "\n" + conversation_side + "\n--------\n"

        messages = [SystemMessagePromptTemplate.from_template(system_prompt)]
        if first_user_message:
            logger.debug("Adding first user message to the prompt")
            messages.append(
                HumanMessagePromptTemplate.from_template(first_user_message)
            )
        chat_template = ChatPromptTemplate.from_messages(messages)

        quality_name = self.config["quality_aspect_name"]
        quality_description = self.config["quality_aspect_description"]
        quality_aspect_instruction = self.config["quality_aspect_instruction"]

        logger.debug(
            "Setting quality aspect details: name=%s, description=%s, instruction=%s",
            quality_name,
            quality_description,
            quality_aspect_instruction,
        )

        chat_template = chat_template.partial(
            quality_aspect_name=quality_name,
            quality_aspect_description=quality_description,
            quality_aspect_instruction=quality_aspect_instruction,
        )

        logger.info("Prompt creation completed")
        return chat_template
