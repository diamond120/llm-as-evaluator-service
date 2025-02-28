from typing import Any, Dict, List

from pydantic import BaseModel, Field


class TaggingEvaluatorInputSchema(BaseModel):
    tagging_rules: str = Field(
        ...,
        description="Details of the tagging task.",
    )
    conversation: List[Any] = Field(
        ..., description="Text of the conversation to be analyzed and tagged."
    )


class TaggingResult(BaseModel):
    """Stores the outcome of the tagging task."""

    tags: List[str] = Field(..., description="List of tags generated from the task.")
