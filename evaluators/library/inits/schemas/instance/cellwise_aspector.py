from typing import Any

from pydantic import BaseModel, Field

from evaluators.library.inits.schemas.instance.aspector import (
    AspectorEvaluatorInputSchema,
    QualityAspect,
)


class CellwiseAspectorEvaluatorInputSchema(BaseModel):
    quality_aspect: QualityAspect = Field(
        ...,
        description="The quality aspect to focus on during the evaluation, including its name and specific instructions.",
    )
    conversation: list[Any] = Field(
        ..., description="The conversation text to be evaluated."
    )
    metadata: dict[str, Any] = Field(
        ..., description="Metadata related to the conversation."
    )


class CellwiseAspectFeedbackItem(BaseModel):
    """Evaluation result for a single cell"""

    Q1_issues: list[str] = Field(
        ..., description="A concrete list of issues in the cell. 15 words or less each."
    )
    Q2_score: int = Field(
        description="A score representing how good the cell is in the given quality aspect, 1 is terrible, 5 is exemplary and flawless.",
        ge=1,
        le=5,
    )
