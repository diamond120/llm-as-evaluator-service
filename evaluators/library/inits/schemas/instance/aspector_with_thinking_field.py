from typing import Any

from pydantic import BaseModel, Field

from evaluators.library.single_stage_system_prompt_aspector import AspectorRole


class AspectFeedbackWithThinking(BaseModel):
    """Evaluation result"""

    analysis: str = Field(
        description="A detailed analysis of the thinking process to evaluate the conversation. Let's take a deep breath and think about it and write it down here before the issues and the score."
    )
    issues: list[str] = Field(
        description="A concrete list of issues in the conversation. 15 words or less each."
    )
    score: int = Field(
        description="A score representing how good the conversation is in the given quality aspect, 1 is terrible, 5 is exemplary and flawless.",
        ge=1,
        le=5,
    )
