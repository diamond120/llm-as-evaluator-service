from typing import Any

from pydantic import BaseModel, Field


class EvaluatorTypeConfigSchemaAspector(BaseModel):
    """Evaluator type"""

    system_prompt: str = Field(
        ..., description="The system prompt configuration as a string."
    )
    first_user_message: str = Field(
        ..., description="The first user message in the conversation."
    )
    role_map: dict[str, str] = Field(
        ...,
        description="A mapping of roles in the conversation, e.g., 'user', 'assistant', 'all' from AspectorRole.",
    )
