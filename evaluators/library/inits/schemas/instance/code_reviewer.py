from typing import Any, Dict, List

from pydantic import BaseModel, Field

from evaluators.library.inits.schemas.instance.generic_task_list import TaskInputSchema


class CodeReviewerInputSchema(BaseModel):
    name: str = Field(..., description="Name of the code review task.")
    instruction: str = Field(
        ..., description="Detailed instructions for performing the code review task."
    )


class CodeReviewerEvaluatorInputSchema(BaseModel):
    grading_rules: str = Field(
        ..., description="The set of rules used for grading the code review."
    )
    conversation: List[Any] = Field(
        ..., description="Conversation or code snippets to be reviewed."
    )
    metadata: Dict[str, Any] = Field(
        ..., description="Additional information relevant to the code review."
    )


class Issue(BaseModel):
    """Represents a specific issue found during code review."""

    cell_position: int = Field(
        ..., description="The position of the cell where the issue was found."
    )
    what: str = Field(..., description="A brief description of the issue.")
    why: str = Field(..., description="Explanation of why this is an issue.")
    where: str = Field(
        ...,
        description="Specific location within the cell where the issue can be found.",
    )
    fix: str = Field(
        ..., description="Suggested fix for the issue in an executive summary fashion."
    )


class CodeReview(BaseModel):
    """Represents the outcome of a code review task."""

    critical_severity_issues: List[Issue] = Field(
        default_factory=list,
        description="List of critical severity issues that majorly decrease the usefulness of the Assistant code replies for the human user.",
    )
    medium_severity_issues: List[Issue] = Field(
        default_factory=list,
        description="List of medium severity issues that have a strong influence on the conversation flow and usefulness.",
    )
    could_have_been_better_issues: List[Issue] = Field(
        default_factory=list,
        description="List of minor issues or suggestions that have almost no influence on the overall score but could improve the quality.",
    )
    scoring_explanation: str = Field(
        ...,
        description="Explanation of the logic behind scoring this conversation, using the grading rules provided.",
    )
    score: int | None = Field(
        ...,
        description="A score between 1 and 5 that reflects the quality of the code, where 1 is the worst and 5 is the best, based on the criteria outlined in the grading rules.",
    )
