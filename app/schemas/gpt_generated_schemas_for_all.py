from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    evaluator_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    engagements_count: Optional[int] = None
    projects_count: Optional[int] = None
    batch_count: Optional[int] = None
    run_count: Optional[int] = None
    evaluation_count: Optional[int] = None
    total_prompt_tokens: Optional[int] = None
    total_generate_tokens: Optional[int] = None
    engagement_id: Optional[int] = None
    project_id: Optional[int] = None
    run_id: Optional[int] = None
    prompt_tokens_used: Optional[int] = None
    generate_tokens_used: Optional[int] = None

    class Config:
        orm_mode = True

    def dict(self, *args, **kwargs):
        kwargs["exclude_none"] = True
        kwargs["exclude_unset"] = True
        return super().dict(*args, **kwargs)

    def json(self, *args, **kwargs):
        kwargs["exclude_none"] = True
        kwargs["exclude_unset"] = True
        return super().json(*args, **kwargs)


class EngagementBase(BaseModel):
    name: str
    description: Optional[str] = None


class EngagementCreate(EngagementBase):
    webhook_url: Optional[str] = None
    auth_token: Optional[str] = None


class EngagementUpdate(EngagementBase):
    pass


class Engagement(EngagementBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class RoleBase(BaseModel):
    name: str


class RoleCreate(RoleBase):
    pass


class RoleUpdate(RoleBase):
    pass


class Role(RoleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    api_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    is_service_account: Optional[bool] = False


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    pass


class User(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ProjectBase(BaseModel):
    engagement_id: int
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserProjectRoleBase(BaseModel):
    user_id: int
    project_id: int
    role_id: int
    is_active: Optional[bool] = True


class UserProjectRoleCreate(UserProjectRoleBase):
    pass


class UserProjectRoleUpdate(UserProjectRoleBase):
    pass


class UserProjectRole(UserProjectRoleBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class BatchRunBase(BaseModel):
    name: str
    inputs: Any
    input_type: str
    user_project_role_id: int


class BatchRun(BatchRunBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class EvaluationBase(BaseModel):
    run_id: int
    batch_run_id: Optional[int] = None
    evaluator_id: Optional[int] = None
    user_project_role_id: int
    name: str
    status: str
    config: dict
    output: Optional[dict] = None
    prompt_tokens_used: Optional[int] = 0
    generate_tokens_used: Optional[int] = 0
    is_aggregator: Optional[bool] = False
    is_used_for_aggregation: Optional[bool] = False
    fail_reason: Optional[str] = None
    evaluator_config_override: Optional[dict] = None
    is_dev: Optional[bool] = False


class Evaluation(EvaluationBase):
    id: int
    uuid_token: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class RunBase(BaseModel):
    batch_run_id: Optional[int] = None
    user_project_role_id: int
    status: str
    item_metadata: Any
    input_hash: str
    stage1_left: int
    stage2_left: Optional[int] = 0
    stage1_failed: Optional[int] = 0
    stage2_failed: Optional[int] = 0
    message: Optional[Any] = None
    evaluations: list[Evaluation] = []


class Run(RunBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class EvaluatorTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    config_schema: Optional[dict] = None


class EvaluatorTypeCreate(EvaluatorTypeBase):
    pass


class EvaluatorTypeUpdate(EvaluatorTypeBase):
    pass


class EvaluatorType(EvaluatorTypeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class EvaluatorBase(BaseModel):
    name: str
    evaluator_type_id: int
    creator_id: int
    description: Optional[str] = None
    config: Optional[dict] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_params: Optional[dict] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None


class EvaluatorCreate(EvaluatorBase):
    pass


class EvaluatorUpdate(EvaluatorBase):
    pass


class Evaluator(EvaluatorBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class OnboardUserRequest(BaseModel):
    engagement_id: Optional[int] = None
    new_project_name: Optional[str] = None
    new_user_email: Optional[str] = None
    new_user_name: Optional[str] = None
    project_id: Optional[int] = None
    role_id: Optional[int] = None
    user_id: Optional[int] = None


class OnboardUserResponse(BaseModel):
    status: str
    message: Optional[str] = None
    token: Optional[str] = None
    user_id: Optional[int] = None
