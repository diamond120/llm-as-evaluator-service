from typing import Any

from pydantic import BaseModel, Field


class TaskInputSchema(BaseModel):
    name: str = Field(..., description="The name of the task.")
    instruction: str = Field(
        ..., description="Instructions & details on how to execute a task."
    )


class GenericTaskEvaluatorInputSchema(BaseModel):
    task: TaskInputSchema = Field(
        ...,
        description="The task to execute, including its name and specific instructions.",
    )
    conversation: list[Any] = Field(
        ..., description="The conversation text to be worked on."
    )
    metadata: dict[str, Any] = Field(
        ..., description="Metadata related to the conversation."
    )


class TaskResult(BaseModel):
    """Result of the task"""

    task_result: list[str] = Field(..., description="Task output as a list of strings.")
