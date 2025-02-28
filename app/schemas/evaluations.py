from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class EvaluationModel(BaseModel):
    id: Optional[int] = Field(None, description="The ID of the evaluation")
    run_id: int = Field(..., description="The associated run ID")
    evaluator_id: Optional[int] = Field(None, description="The associated evaluator ID")
    evaluator_name: Optional[str] = Field(
        None, description="The name of the evaluator"
    )  # Added field
    name: str = Field(..., description="The name of the evaluation")
    status: str = Field(..., description="The status of the evaluation")
    config: Optional[Dict] = Field(
        None, description="Configuration JSON for the evaluation"
    )
    output: Optional[Dict] = Field(None, description="Output JSON of the evaluation")
    prompt_tokens_used: int = Field(0, description="Number of prompt tokens used")
    generate_tokens_used: int = Field(0, description="Number of generate tokens used")
    is_aggregator: bool = Field(False, description="Is this evaluation an aggregator?")
    is_used_for_aggregation: bool = Field(
        False, description="Is this used for aggregation?"
    )
    fail_reason: Optional[str] = Field(
        None, description="Reason for evaluation failure, if any"
    )
    evaluator_config_override: Optional[Dict] = Field(
        None, description="Evaluator configuration overrides"
    )
    is_dev: bool = Field(False, description="Is this a development evaluation?")

    class Config:
        orm_mode = True


class EvaluationBaseModel(BaseModel):
    id: int
    run_id: int
    project_id: int

    class Config:
        orm_mode = True


class BatchRunGroupedModel(BaseModel):
    batch_name: str
    evaluations: List[EvaluationModel]

    class Config:
        orm_mode = True


class ResultModel(BaseModel):
    result: List[BatchRunGroupedModel]


class ProjectModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""

    class Config:
        orm_mode = True


class BatchRunResponse(BaseModel):
    engagement: Optional[str]
    project: Optional[str]
    batch_name: Optional[str]
    runs: List[Dict[str, Union[int, str]]]
