from pydantic import BaseModel, Field


class EvaluatorTypeConfigSchemaCellwiseAspector(BaseModel):
    """Evaluator type"""

    system_prompt: str = Field(
        ..., description="The system prompt configuration as a string."
    )
    first_user_message: str = Field(
        ..., description="The first user message in the conversation."
    )
