import operator
from typing import Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel


class AgentMetadata(BaseModel):
    identity: str
    quality_evaluation_rules: str
    quality_dimension_name: str
    quality_guidelines: str
    what_not_to_do: str


class State(TypedDict):
    user_prompt: str
    last_ai_reply: str
    extra_latest_ai_reply: str
    conversation_metadata: str
    meta_review_result: dict
    filtered_issues: Annotated[list[tuple], operator.add]
    results_for_meta_review: Annotated[list[tuple], operator.add]