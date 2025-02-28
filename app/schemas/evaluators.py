from typing import Dict, List, Optional

from pydantic import BaseModel


class ProjectModel(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class EvaluatorTypeModel(BaseModel):
    id: int
    name: str
    config_schema: str | dict
    description: str | None

    class Config:
        orm_mode = True


class EvaluationModel(BaseModel):
    id: int
    name: str
    status: str

    class Config:
        orm_mode = True


class EvaluationConfigModel(BaseModel):
    id: int
    config_detail: str  # Example field

    class Config:
        orm_mode = True


class EvaluatorConfigModel(BaseModel):
    id: int
    config_detail: str  # Example field

    class Config:
        orm_mode = True


class EvaluatorModel(BaseModel):
    # do not provide defaults here, upsert will break
    id: Optional[int] = None  # Assuming you have an ID field from TimestampedBase
    name: str
    evaluator_type_id: Optional[int] = None
    project_id: Optional[int] = None
    description: str
    config: dict | str
    llm_provider: str
    llm_model: str
    llm_params: dict | str
    input_schema: dict | str
    output_schema: dict | str
    # evaluations: List[EvaluationModel] = []
    # evaluation_configs: List[EvaluationConfigModel] = []
    # evaluator_configs: List[EvaluatorConfigModel] = []
    project: Optional[ProjectModel] = None
    evaluator_type: Optional[EvaluatorTypeModel] = None
    evaluator_type_name: Optional[str] = None

    class Config:
        orm_mode = True


class EvaluatorPartialUpdateModel(BaseModel):
    # do not provide defaults here, upsert will break
    id: Optional[int] = None  # Assuming you have an ID field from TimestampedBase
    name: str
    evaluator_type_id: Optional[int] = None
    project_id: Optional[int] = None
    description: Optional[str] = None
    config: Optional[dict | str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_params: Optional[dict | str] = None
    input_schema: Optional[dict | str] = None
    output_schema: Optional[dict | str] = None
    # evaluations: List[EvaluationModel] = []
    # evaluation_configs: List[EvaluationConfigModel] = []
    # evaluator_configs: List[EvaluatorConfigModel] = []
    project: Optional[ProjectModel] = None
    evaluator_type: Optional[EvaluatorTypeModel] = None
    evaluator_type_name: Optional[str] = None

    class Config:
        orm_mode = True


class EvaluatorUpsertModel(BaseModel):
    evaluator: EvaluatorModel
    action: str


class EvaluatorSummary(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        orm_mode = True
