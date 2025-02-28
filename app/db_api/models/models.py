import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db_api.models.base import TimestampedBase

CONST = ""  # "llm_eval__"


class Engagement(TimestampedBase):
    __tablename__ = CONST + "engagement"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True)
    description = Column(String(300))
    webhook_url = Column(String(1100), nullable=True)
    auth_token = Column(String(1100), nullable=True)
    projects = relationship("Project", back_populates="engagement")

    __table_args__ = (
        UniqueConstraint("name", name="_engname_uc"),
        Index("idx_engagement_name", "name"),
    )


class Role(TimestampedBase):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True)
    user_project_role = relationship("UserProjectRole", back_populates="role")

    __table_args__ = (
        UniqueConstraint("name", name="_role_uc"),
        Index("idx_role_name", "name"),
    )


class User(TimestampedBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(200), index=True)
    name = Column(String(150))
    profile_pic = Column(String(200), nullable=True)
    api_token = Column(String(1000), nullable=True)
    client_id = Column(String(300), nullable=True)
    client_secret = Column(String(300), nullable=True)
    is_service_account = Column(Boolean, default=False)
    user_project_role = relationship("UserProjectRole", back_populates="user")

    __table_args__ = (
        UniqueConstraint("email", name="_user_email_uc"),
        Index("idx_user_email", "email"),
    )


class Project(TimestampedBase):
    __tablename__ = CONST + "project"
    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey(CONST + "engagement.id"))
    name = Column(String(150))
    description = Column(String(300))

    engagement = relationship("Engagement", back_populates="projects")
    user_project_role = relationship("UserProjectRole", back_populates="project")

    __table_args__ = (
        UniqueConstraint("engagement_id", "name", name="_engagement_project_uc"),
        Index("idx_project_engagement_id", "engagement_id"),
        Index("idx_project_name", "name"),
    )


class UserProjectRole(TimestampedBase):
    __tablename__ = "user_project_roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey(CONST + "project.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="user_project_role")
    project = relationship("Project", back_populates="user_project_role")
    role = relationship("Role", back_populates="user_project_role")
    batch_runs = relationship("BatchRun", back_populates="user_project_role")
    runs = relationship("Run", back_populates="user_project_role")
    evaluations = relationship("Evaluation", back_populates="user_project_role")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "project_id", "role_id", name="_userrole_project_uc"
        ),
        Index("idx_user_project_role_user_id", "user_id"),
        Index("idx_user_project_role_project_id", "project_id"),
        Index("idx_user_project_role_role_id", "role_id"),
    )


class BatchRun(TimestampedBase):
    __tablename__ = CONST + "batch_run"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150))
    inputs = Column(JSON)
    input_type = Column(String(20))
    user_project_role_id = Column(Integer, ForeignKey("user_project_roles.id"))

    user_project_role = relationship("UserProjectRole", back_populates="batch_runs")
    runs = relationship("Run", back_populates="batch_run")

    __table_args__ = (
        Index("idx_batch_run_user_project_role_id", "user_project_role_id"),
    )


class Run(TimestampedBase):
    __tablename__ = CONST + "run"
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_run_id = Column(Integer, ForeignKey(CONST + "batch_run.id"), nullable=True)
    user_project_role_id = Column(Integer, ForeignKey("user_project_roles.id"))

    status = Column(String(15))
    item_metadata = Column(JSON)
    input_hash = Column(String(256))
    stage1_left = Column(Integer)
    stage2_left = Column(Integer, default=0)
    stage1_failed = Column(Integer, default=0)
    stage2_failed = Column(Integer, default=0)
    evaluations = relationship("Evaluation", back_populates="run")
    user_project_role = relationship("UserProjectRole", back_populates="runs")
    batch_run = relationship("BatchRun", back_populates="runs")
    message = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_run_batch_run_id", "batch_run_id"),
        Index("idx_run_user_project_role_id", "user_project_role_id"),
    )


class Evaluation(TimestampedBase):
    __tablename__ = CONST + "evaluation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey(CONST + "run.id"))
    batch_run_id = Column(Integer, ForeignKey(CONST + "batch_run.id"), nullable=True)
    evaluator_id = Column(Integer, ForeignKey(CONST + "evaluator.id"), nullable=True)
    user_project_role_id = Column(Integer, ForeignKey("user_project_roles.id"))

    name = Column(String(150))
    status = Column(String(15))
    config = Column(JSON)
    output = Column(JSON)
    prompt_tokens_used = Column(Integer, default=0)
    generate_tokens_used = Column(Integer, default=0)
    is_aggregator = Column(Boolean, default=False)
    is_used_for_aggregation = Column(Boolean, default=False)
    fail_reason = Column(String(1000), nullable=True)
    run = relationship("Run", back_populates="evaluations")
    evaluator_config_override = Column(JSON, nullable=True)
    is_dev = Column(Boolean, default=False)

    evaluator = relationship("Evaluator", back_populates="evaluations")
    user_project_role = relationship("UserProjectRole", back_populates="evaluations")
    uuid_token = Column(String(36), default=lambda: str(uuid.uuid4()), nullable=False)

    __table_args__ = (
        Index("idx_run_id", "run_id"),
        Index("idx_batch_run_id", "batch_run_id"),
        Index("idx_user_project_role_id", "user_project_role_id"),
        Index("idx_uuid_token", "uuid_token"),
    )


class EvaluatorType(TimestampedBase):
    __tablename__ = CONST + "evaluator_type"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True)
    description = Column(String(300))
    config_schema = Column(JSON)
    evaluators = relationship("Evaluator", back_populates="evaluator_type")

    __table_args__ = (Index("idx_evaluator_type_name", "name"),)


class Evaluator(TimestampedBase):
    __tablename__ = CONST + "evaluator"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True)
    evaluator_type_id = Column(Integer, ForeignKey(CONST + "evaluator_type.id"))
    creator_id = Column(Integer, ForeignKey(CONST + "users.id"))

    description = Column(String(300))
    config = Column(JSON)
    llm_provider = Column(String(80))
    llm_model = Column(String(100))
    llm_params = Column(JSON)
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    evaluations = relationship("Evaluation", back_populates="evaluator")
    evaluation_configs = relationship("EvaluationConfig", back_populates="evaluator")
    evaluator_configs = relationship("EvaluatorConfig", back_populates="evaluator")
    evaluator_type = relationship("EvaluatorType", back_populates="evaluators")

    __table_args__ = (
        UniqueConstraint("name", name="_eval_uc"),
        Index("idx_evaluator_name", "name"),
        Index("idx_evaluator_type_id", "evaluator_type_id"),
        Index("idx_creator_id", "creator_id"),
    )


class EvaluatorHistory(TimestampedBase):
    __tablename__ = CONST + "evaluator_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer)
    data = Column(JSON)


class EvaluationConfig(TimestampedBase):
    __tablename__ = CONST + "evaluation_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluator_id = Column(Integer, ForeignKey(CONST + "evaluator.id"))
    config = Column(JSON)

    evaluator = relationship("Evaluator", back_populates="evaluation_configs")

    __table_args__ = (Index("idx_evaluation_config_evaluator_id", "evaluator_id"),)


class EvaluatorConfig(TimestampedBase):
    __tablename__ = CONST + "evaluator_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluator_id = Column(Integer, ForeignKey(CONST + "evaluator.id"))
    config = Column(JSON)
    llm_config = Column(JSON)
    input_schema = Column(JSON)
    output_schema = Column(JSON)

    evaluator = relationship("Evaluator", back_populates="evaluator_configs")

    __table_args__ = (Index("idx_evaluator_config_evaluator_id", "evaluator_id"),)


class LLMPricing(TimestampedBase):
    __tablename__ = "llm_pricing"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(100), index=True, nullable=False)
    model = Column(String(100), index=True, nullable=False)
    version = Column(String(100), index=True, nullable=True)
    input_price_per_million_tokens = Column(Float, nullable=False)
    output_price_per_million_tokens = Column(Float, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    class Config:
        orm_mode = True

    __table_args__ = (
        Index("idx_llmpricing_model", "model"),
        Index("idx_llmpricing_provider", "provider"),
        Index("idx_llmpricing_effective_from", "effective_from"),
        Index("idx_llmpricing_effective_to", "effective_to"),
    )
