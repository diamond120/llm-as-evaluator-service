from pydantic import BaseModel, Field

SCORING_MESSAGES_PROMPT = [
    [
        "system",
        """You are an expert at scoring a task based on found issues.

Please follow the outlined scoring rules and evaluate the provided list of turns and issues:
<|SCORING RULES START|>
{quality_aspect}
<|SCORING RULES END|>

Show your step by step process in the `before_scoring` field.
DO NOT COPY PASTE PROVIDED DATA. THINK.
""",
    ],
    [
        "human",
        """Here are the issues found in the task during its review:

<|FOUND ISSUES START|>
{evaluations}
<|FOUND ISSUES START|>
Please, proceed to score the review now!
""",
    ],
]


class ScoringOutput(BaseModel):
    """Score output"""

    before_scoring: str = Field(
        ..., description="Place to output your step by step scoring process."
    )
    score: int = Field(..., description="Final score ranging from 1 to 5.", ge=1, le=5)
    short_issues_summary_md: str = Field(
        ...,
        description="A brief markdown scoing explanation without deep details. USE STRUCTURED MARKDOWN.",
    )
