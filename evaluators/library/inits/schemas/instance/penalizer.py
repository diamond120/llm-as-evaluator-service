from typing import Any

from pydantic import BaseModel, Field


class PenalizeEvaluatorInputSchema(BaseModel):
    evaluations: list[dict[str, Any]] = Field(
        ..., description="Stage 1 evaluation reviews to summarize."
    )
    penalize_these: list[str] = Field(
        ..., description="Types of issues to penalize in the evaluations."
    )
    original_input: dict[str, Any] = Field(
        ..., description="The original input data for the evaluations."
    )


class PenalizerOutput(BaseModel):
    """Output for penalizer evaluations"""

    analysis: str = Field(
        ...,
        description="Detailed analysis of the penalization process, including the reasoning behind each penalty applied. Let's think step by step.",
    )
    penalized_summary: str = Field(
        ..., description="A summary of the evaluations with penalties applied."
    )
    score: int = Field(
        ...,
        description="The score reflecting the impact of penalties on the evaluation - below <=3 means we must throw this conversation away from the dataset. 4 is okay, 5 is good to go.",
    )
