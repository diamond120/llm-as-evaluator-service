from typing import Any

from pydantic import BaseModel, Field


class SummarizeEvaluatorInputSchema(BaseModel):
    evaluations: list[dict[str, Any]] = Field(
        ..., description="Stage 1 evaluation reviews to summarize."
    )
    original_input: dict[str, Any] = Field(
        ..., description="The original input data for the evaluations."
    )


class SummaryEvaluation(BaseModel):
    """Summary of the evaluations"""

    summary: str = Field(..., description="A concise summary of the evaluations.")
