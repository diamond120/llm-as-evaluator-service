from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db_api import models
from app.db_api.database import get_db_gen
from app.logging_config import logger
from app.schemas import gpt_generated_schemas_for_all as schemas
from app.utils.auth import create_access_token, get_current_user
from common.utils import load_env

env_vars = load_env()
router = APIRouter(dependencies=[Depends(get_current_user)])


# Utility function to handle not found errors
def get_or_404(model, id, db):
    logger.debug(f"Fetching {model.__name__} with id {id}")
    obj = db.query(model).filter(model.id == id).first()
    if not obj:
        logger.error(f"{model.__name__} with id {id} not found")
        raise HTTPException(status_code=404, detail="Item not found")
    return obj


# Engagement CRUD and Search
@router.post("/engagements/", response_model=schemas.Engagement)
def create_engagement(
    engagement: schemas.EngagementCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating engagement with data: {engagement.dict()}")
    db_engagement = (
        db.query(models.Engagement)
        .filter(models.Engagement.name == engagement.name)
        .first()
    )
    if db_engagement:
        logger.error(f"Engagement with name {engagement.name} already exists")
        raise HTTPException(status_code=400, detail="Engagement already exists")
    db_engagement = models.Engagement(**engagement.dict())
    db.add(db_engagement)
    db.commit()
    db.refresh(db_engagement)
    logger.info(f"Created engagement with id {db_engagement.id}")
    return db_engagement


@router.get("/engagements", response_model=List[schemas.Engagement])
def read_engagements(
    engagement_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading engagements with filters - id: {engagement_id}, name: {name}, description: {description}"
    )
    if engagement_id is not None:
        return [get_or_404(models.Engagement, engagement_id, db)]

    query = db.query(models.Engagement)
    if name:
        query = query.filter(models.Engagement.name.contains(name))
    if description:
        query = query.filter(models.Engagement.description.contains(description))
    query = query.order_by(models.Engagement.name.asc())
    results = query.all()
    logger.info(f"Found {len(results)} engagements")
    return results


@router.put("/engagements/{engagement_id}", response_model=schemas.Engagement)
def update_engagement(
    engagement_id: int,
    engagement: schemas.EngagementUpdate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Updating engagement with id {engagement_id} with data: {engagement.dict(exclude_unset=True)}"
    )
    db_engagement = get_or_404(models.Engagement, engagement_id, db)
    for key, value in engagement.dict(exclude_unset=True).items():
        setattr(db_engagement, key, value)
    db.commit()
    db.refresh(db_engagement)
    logger.info(f"Updated engagement with id {db_engagement.id}")
    return db_engagement


# Role CRUD and Search
@router.post("/roles/", response_model=schemas.Role)
def create_role(
    role: schemas.RoleCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating role with data: {role.dict()}")
    db_role = models.Role(**role.dict())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    logger.info(f"Created role with id {db_role.id}")
    return db_role


@router.get("/roles", response_model=List[schemas.Role])
def read_roles(
    role_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Reading roles with filters - id: {role_id}, name: {name}")
    if role_id is not None:
        return [get_or_404(models.Role, role_id, db)]

    query = db.query(models.Role)
    if name:
        query = query.filter(models.Role.name.contains(name))
    query = query.order_by(models.Role.updated_at.desc())
    results = query.all()
    logger.info(f"Found {len(results)} roles")
    return results


@router.put("/roles/{role_id}", response_model=schemas.Role)
def update_role(
    role_id: int,
    role: schemas.RoleUpdate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Updating role with id {role_id} with data: {role.dict(exclude_unset=True)}"
    )
    db_role = get_or_404(models.Role, role_id, db)
    for key, value in role.dict(exclude_unset=True).items():
        setattr(db_role, key, value)
    db.commit()
    db.refresh(db_role)
    logger.info(f"Updated role with id {db_role.id}")
    return db_role


# User CRUD and Search
@router.post("/users/", response_model=schemas.User)
def create_user(
    user_instance: schemas.UserCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating user with data: {user_instance.dict()}")
    db_user = models.User(**user_instance.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Created user with id {db_user.id}")
    return db_user


@router.get("/users", response_model=List[schemas.User])
def read_users(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading users with filters - id: {user_id}, email: {email}, name: {name}"
    )
    if user_id is not None:
        return [get_or_404(models.User, user_id, db)]

    query = db.query(models.User)
    if email:
        query = query.filter(models.User.email.contains(email))
    if name:
        query = query.filter(models.User.name.contains(name))
    query = query.order_by(models.User.email.asc())
    results = query.all()
    logger.info(f"Found {len(results)} users")
    return results


@router.put("/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Updating user with id {user_id} with data: {user.dict(exclude_unset=True)}"
    )
    db_user = get_or_404(models.User, user_id, db)
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Updated user with id {db_user.id}")
    return db_user


# Project CRUD and Search
@router.post("/projects/", response_model=schemas.Project)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating project with data: {project.dict()}")
    db_project = models.Project(**project.dict())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    logger.info(f"Created project with id {db_project.id}")
    return db_project


@router.get("/projects", response_model=List[schemas.Project])
def read_projects(
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading projects with filters - id: {project_id}, name: {name}, description: {description}, skip: {skip}, limit: {limit}"
    )
    if project_id is not None:
        return [get_or_404(models.Project, project_id, db)]

    query = db.query(models.Project)
    if name:
        query = query.filter(models.Project.name.contains(name))
    if description:
        query = query.filter(models.Project.description.contains(description))
    query = query.order_by(models.Project.name.asc()).offset(skip).limit(limit)
    results = query.all()
    logger.info(f"Found {len(results)} projects")
    return results


@router.put("/projects/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    project: schemas.ProjectUpdate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Updating project with id {project_id} with data: {project.dict(exclude_unset=True)}"
    )
    db_project = get_or_404(models.Project, project_id, db)
    for key, value in project.dict(exclude_unset=True).items():
        setattr(db_project, key, value)
    db.commit()
    db.refresh(db_project)
    logger.info(f"Updated project with id {db_project.id}")
    return db_project


# UserProjectRole CRUD and Search
@router.post("/user_project_roles/", response_model=schemas.UserProjectRole)
def create_user_project_role(
    user_project_role: schemas.UserProjectRoleCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating user project role with data: {user_project_role.dict()}")
    db_user_project_role = models.UserProjectRole(**user_project_role.dict())
    db.add(db_user_project_role)
    db.commit()
    db.refresh(db_user_project_role)
    logger.info(f"Created user project role with id {db_user_project_role.id}")
    return db_user_project_role


@router.get("/user_project_roles", response_model=List[schemas.UserProjectRole])
def read_user_project_roles(
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    role_id: Optional[int] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading user project roles with filters - user_id: {user_id}, project_id: {project_id}, role_id: {role_id}, skip: {skip}, limit: {limit}"
    )
    query = db.query(models.UserProjectRole)
    if user_id:
        query = query.filter(models.UserProjectRole.user_id == user_id)
    if project_id:
        query = query.filter(models.UserProjectRole.project_id == project_id)
    if role_id:
        query = query.filter(models.UserProjectRole.role_id == role_id)
    query = (
        query.order_by(models.UserProjectRole.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    results = query.all()
    logger.info(f"Found {len(results)} user project roles")
    return results


@router.get("/batch_runs", response_model=List[schemas.BatchRun])
def read_batch_runs(
    batch_run_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    input_type: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading batch runs with filters - id: {batch_run_id}, name: {name}, input_type: {input_type}, skip: {skip}, limit: {limit}"
    )
    if batch_run_id is not None:
        return [get_or_404(models.BatchRun, batch_run_id, db)]

    query = db.query(models.BatchRun)
    if name:
        query = query.filter(models.BatchRun.name.contains(name))
    if input_type:
        query = query.filter(models.BatchRun.input_type.contains(input_type))
    query = query.order_by(models.BatchRun.updated_at.desc()).offset(skip).limit(limit)
    results = query.all()
    logger.info(f"Found {len(results)} batch runs")
    return results


@router.get("/runs", response_model=List[schemas.Run])
def read_runs(
    run_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    input_hash: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading runs with filters - id: {run_id}, status: {status}, input_hash: {input_hash}, skip: {skip}, limit: {limit}"
    )
    if run_id is not None:
        return [get_or_404(models.Run, run_id, db)]

    query = db.query(models.Run)
    if status:
        query = query.filter(models.Run.status.contains(status))
    if input_hash:
        query = query.filter(models.Run.input_hash.contains(input_hash))
    query = query.order_by(models.Run.updated_at.desc()).offset(skip).limit(limit)
    results = query.all()
    logger.info(f"Found {len(results)} runs")
    return results


@router.get("/evaluations", response_model=List[schemas.Evaluation])
def read_evaluations(
    evaluation_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading evaluations with filters - id: {evaluation_id}, name: {name}, status: {status}, skip: {skip}, limit: {limit}"
    )
    if evaluation_id is not None:
        return [get_or_404(models.Evaluation, evaluation_id, db)]

    query = db.query(models.Evaluation)
    if name:
        query = query.filter(models.Evaluation.name.contains(name))
    if status:
        query = query.filter(models.Evaluation.status.contains(status))
    query = (
        query.order_by(models.Evaluation.updated_at.desc()).offset(skip).limit(limit)
    )
    results = query.all()
    logger.info(f"Found {len(results)} evaluations")
    return results


# EvaluatorType CRUD and Search
@router.post("/evaluator_types/", response_model=schemas.EvaluatorType)
def create_evaluator_type(
    evaluator_type: schemas.EvaluatorTypeCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating evaluator type with data: {evaluator_type}")
    db_evaluator_type = models.EvaluatorType(**evaluator_type.dict())
    db.add(db_evaluator_type)
    db.commit()
    db.refresh(db_evaluator_type)
    logger.info(f"Created evaluator type with ID: {db_evaluator_type.id}")
    return db_evaluator_type


@router.get("/evaluator_types", response_model=List[schemas.EvaluatorType])
def read_evaluator_types(
    evaluator_type_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading evaluator types with filters - id: {evaluator_type_id}, name: {name}, skip: {skip}, limit: {limit}"
    )
    if evaluator_type_id is not None:
        return [get_or_404(models.EvaluatorType, evaluator_type_id, db)]

    query = db.query(models.EvaluatorType)
    if name:
        query = query.filter(models.EvaluatorType.name.contains(name))
    query = (
        query.order_by(models.EvaluatorType.updated_at.desc()).offset(skip).limit(limit)
    )
    results = query.all()
    logger.info(f"Found {len(results)} evaluator types")
    return results


@router.put(
    "/evaluator_types/{evaluator_type_id}", response_model=schemas.EvaluatorType
)
def update_evaluator_type(
    evaluator_type_id: int,
    evaluator_type: schemas.EvaluatorTypeUpdate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Updating evaluator type with ID: {evaluator_type_id} with data: {evaluator_type}"
    )
    db_evaluator_type = get_or_404(models.EvaluatorType, evaluator_type_id, db)
    for key, value in evaluator_type.dict(exclude_unset=True).items():
        setattr(db_evaluator_type, key, value)
    db.commit()
    db.refresh(db_evaluator_type)
    logger.info(f"Updated evaluator type with ID: {db_evaluator_type.id}")
    return db_evaluator_type


# Evaluator CRUD and Search
@router.post("/evaluators/", response_model=schemas.Evaluator)
def create_evaluator(
    evaluator: schemas.EvaluatorCreate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Creating evaluator with data: {evaluator}")
    db_evaluator = models.Evaluator(**evaluator.dict())
    db.add(db_evaluator)
    db.commit()
    db.refresh(db_evaluator)
    logger.info(f"Created evaluator with ID: {db_evaluator.id}")
    return db_evaluator


@router.get("/evaluators", response_model=List[schemas.Evaluator])
def read_evaluators(
    evaluator_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    name: Optional[str] = None,
    llm_provider: Optional[str] = None,
    db: Session = Depends(get_db_gen),
):
    logger.debug(
        f"Reading evaluators with filters - id: {evaluator_id}, name: {name}, llm_provider: {llm_provider}, skip: {skip}, limit: {limit}"
    )
    if evaluator_id is not None:
        return [get_or_404(models.Evaluator, evaluator_id, db)]

    query = db.query(models.Evaluator)
    if name:
        query = query.filter(models.Evaluator.name.contains(name))
    if llm_provider:
        query = query.filter(models.Evaluator.llm_provider.contains(llm_provider))
    query = query.order_by(models.Evaluator.updated_at.desc()).offset(skip).limit(limit)
    results = query.all()
    logger.info(f"Found {len(results)} evaluators")
    return results


@router.put("/evaluators/{evaluator_id}", response_model=schemas.Evaluator)
def update_evaluator(
    evaluator_id: int,
    evaluator: schemas.EvaluatorUpdate,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Updating evaluator with ID: {evaluator_id} with data: {evaluator}")
    db_evaluator = get_or_404(models.Evaluator, evaluator_id, db)
    for key, value in evaluator.dict(exclude_unset=True).items():
        setattr(db_evaluator, key, value)
    db.commit()
    db.refresh(db_evaluator)
    logger.info(f"Updated evaluator with ID: {db_evaluator.id}")
    return db_evaluator


@router.get("/stats/{what}/{what_id}", response_model=schemas.StatsResponse)
def get_stats(
    what: str,
    what_id: int,
    db: Session = Depends(get_db_gen),
):
    logger.debug(f"Getting stats for {what} with ID: {what_id}")
    if what == "engagement":
        return get_engagement_stats(what_id, db)
    elif what == "project":
        return get_project_stats(what_id, db)
    elif what == "batch":
        return get_batch_stats(what_id, db)
    elif what == "run":
        return get_run_stats(what_id, db)
    elif what == "evaluation":
        return get_evaluation_stats(what_id, db)
    elif what == "evaluator":
        return get_evaluator_stats(what_id, db)
    else:
        logger.error(f"Invalid stats type: {what}")
        raise HTTPException(status_code=400, detail="Invalid stats type")


def get_evaluator_stats(evaluator_id: int, db: Session) -> dict[str, Any]:
    logger.debug(f"Getting evaluator stats for ID: {evaluator_id}")
    evaluator = db.query(models.Evaluator).filter_by(id=evaluator_id).first()
    if not evaluator:
        logger.error(f"Evaluator not found with ID: {evaluator_id}")
        raise HTTPException(status_code=404, detail="Item not found")

    evaluation_query = (
        db.query(
            func.count(models.Evaluation.id).label("evaluation_count"),
            func.coalesce(func.sum(models.Evaluation.prompt_tokens_used), 0).label(
                "total_prompt_tokens"
            ),
            func.coalesce(func.sum(models.Evaluation.generate_tokens_used), 0).label(
                "total_generate_tokens"
            ),
        )
        .filter_by(evaluator_id=evaluator_id)
        .first()
    )

    evaluation_count = evaluation_query.evaluation_count
    total_prompt_tokens = evaluation_query.total_prompt_tokens
    total_generate_tokens = evaluation_query.total_generate_tokens

    run_count = (
        db.query(func.count(models.Run.id.distinct()))
        .join(models.Evaluation)
        .filter(models.Evaluation.evaluator_id == evaluator_id)
        .scalar()
    )

    batch_count = (
        db.query(func.count(models.BatchRun.id.distinct()))
        .join(models.Run)
        .join(models.Evaluation)
        .filter(models.Evaluation.evaluator_id == evaluator_id)
        .scalar()
    )

    project_count = (
        db.query(func.count(models.Project.id.distinct()))
        .join(models.UserProjectRole)
        .join(models.Run)
        .join(models.Evaluation)
        .filter(models.Evaluation.evaluator_id == evaluator_id)
        .scalar()
    )

    engagements_count = (
        db.query(func.count(models.Engagement.id.distinct()))
        .join(models.Project)
        .join(models.UserProjectRole)
        .join(models.Run)
        .join(models.Evaluation)
        .filter(models.Evaluation.evaluator_id == evaluator_id)
        .scalar()
    )

    stats = {
        "evaluator_id": evaluator.id,
        "name": evaluator.name,
        "description": evaluator.description,
        "engagements_count": engagements_count,
        "projects_count": project_count,
        "batch_count": batch_count,
        "run_count": run_count,
        "evaluation_count": evaluation_count,
        "total_prompt_tokens": total_prompt_tokens,
        "total_generate_tokens": total_generate_tokens,
    }
    logger.info(f"Evaluator stats: {stats}")
    return stats


def get_engagement_stats(engagement_id: int, db: Session) -> dict[str, Any]:
    logger.debug(f"Getting engagement stats for ID: {engagement_id}")
    engagement = db.query(models.Engagement).filter_by(id=engagement_id).first()
    if not engagement:
        logger.error(f"Engagement not found with ID: {engagement_id}")
        raise HTTPException(status_code=404, detail="Item not found")

    project_ids = (
        db.query(models.Project.id).filter_by(engagement_id=engagement_id).all()
    )
    project_ids = [project_id[0] for project_id in project_ids]

    batch_count = (
        db.query(func.count(models.BatchRun.id.distinct()))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id.in_(project_ids))
        .scalar()
    )

    run_count = (
        db.query(func.count(models.Run.id.distinct()))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id.in_(project_ids))
        .scalar()
    )

    evaluation_count = (
        db.query(func.count(models.Evaluation.id.distinct()))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id.in_(project_ids))
        .scalar()
    )

    total_prompt_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.prompt_tokens_used), 0))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id.in_(project_ids))
        .scalar()
    )

    total_generate_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.generate_tokens_used), 0))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id.in_(project_ids))
        .scalar()
    )

    stats = {
        "engagement_id": engagement.id,
        "name": engagement.name,
        "description": engagement.description,
        "projects_count": len(project_ids),
        "batch_count": batch_count,
        "run_count": run_count,
        "evaluation_count": evaluation_count,
        "total_prompt_tokens": total_prompt_tokens,
        "total_generate_tokens": total_generate_tokens,
    }
    logger.info(f"Engagement stats: {stats}")
    return stats


def get_run_stats(run_id: int, db: Session) -> dict[str, Any]:
    logger.debug(f"Fetching run stats for run_id: {run_id}")
    run = db.query(models.Run).filter_by(id=run_id).first()
    if not run:
        logger.error(f"Run with id {run_id} not found")
        raise HTTPException(status_code=404, detail="Item not found")

    evaluation_count = (
        db.query(func.count(models.Evaluation.id.distinct()))
        .filter_by(run_id=run_id)
        .scalar()
    )
    logger.debug(f"Evaluation count for run_id {run_id}: {evaluation_count}")

    total_prompt_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.prompt_tokens_used), 0))
        .filter_by(run_id=run_id)
        .scalar()
    )
    logger.debug(f"Total prompt tokens for run_id {run_id}: {total_prompt_tokens}")

    total_generate_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.generate_tokens_used), 0))
        .filter_by(run_id=run_id)
        .scalar()
    )
    logger.debug(f"Total generate tokens for run_id {run_id}: {total_generate_tokens}")

    stats = {
        "run_id": run.id,
        "evaluation_count": evaluation_count,
        "total_prompt_tokens": total_prompt_tokens,
        "total_generate_tokens": total_generate_tokens,
    }
    logger.info(f"Run stats for run_id {run_id}: {stats}")
    return stats


def get_evaluation_stats(evaluation_id: int, db: Session) -> dict[str, Any]:
    logger.debug(f"Fetching evaluation stats for evaluation_id: {evaluation_id}")
    evaluation = db.query(models.Evaluation).filter_by(id=evaluation_id).first()
    if not evaluation:
        logger.error(f"Evaluation with id {evaluation_id} not found")
        raise HTTPException(status_code=404, detail="Item not found")

    stats = {
        "evaluation_id": evaluation.id,
        "name": evaluation.name,
        "prompt_tokens_used": evaluation.prompt_tokens_used,
        "generate_tokens_used": evaluation.generate_tokens_used,
    }
    logger.info(f"Evaluation stats for evaluation_id {evaluation_id}: {stats}")
    return stats


def get_project_stats(project_id: int, db: Session) -> dict[str, Any]:
    logger.debug(f"Fetching project stats for project_id: {project_id}")
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project:
        logger.error(f"Project with id {project_id} not found")
        raise HTTPException(status_code=404, detail="Item not found")

    batch_count = (
        db.query(func.count(models.BatchRun.id.distinct()))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id == project_id)
        .scalar()
    )
    logger.debug(f"Batch count for project_id {project_id}: {batch_count}")

    run_count = (
        db.query(func.count(models.Run.id.distinct()))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id == project_id)
        .scalar()
    )
    logger.debug(f"Run count for project_id {project_id}: {run_count}")

    evaluation_count = (
        db.query(func.count(models.Evaluation.id.distinct()))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id == project_id)
        .scalar()
    )
    logger.debug(f"Evaluation count for project_id {project_id}: {evaluation_count}")

    total_prompt_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.prompt_tokens_used), 0))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id == project_id)
        .scalar()
    )
    logger.debug(
        f"Total prompt tokens for project_id {project_id}: {total_prompt_tokens}"
    )

    total_generate_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.generate_tokens_used), 0))
        .join(models.UserProjectRole)
        .filter(models.UserProjectRole.project_id == project_id)
        .scalar()
    )
    logger.debug(
        f"Total generate tokens for project_id {project_id}: {total_generate_tokens}"
    )

    stats = {
        "project_id": project.id,
        "name": project.name,
        "description": project.description,
        "batch_count": batch_count,
        "run_count": run_count,
        "evaluation_count": evaluation_count,
        "total_prompt_tokens": total_prompt_tokens,
        "total_generate_tokens": total_generate_tokens,
    }
    logger.info(f"Project stats for project_id {project_id}: {stats}")
    return stats


def get_batch_stats(batch_id: int, db: Session) -> dict[str, Any]:
    logger.debug(f"Fetching batch stats for batch_id: {batch_id}")
    batch = db.query(models.BatchRun).filter_by(id=batch_id).first()
    if not batch:
        logger.error(f"Batch with id {batch_id} not found")
        raise HTTPException(status_code=404, detail="Item not found")

    run_count = (
        db.query(func.count(models.Run.id.distinct()))
        .filter_by(batch_run_id=batch_id)
        .scalar()
    )
    logger.debug(f"Run count for batch_id {batch_id}: {run_count}")

    evaluation_count = (
        db.query(func.count(models.Evaluation.id.distinct()))
        .join(models.Run)
        .filter(models.Run.batch_run_id == batch_id)
        .scalar()
    )
    logger.debug(f"Evaluation count for batch_id {batch_id}: {evaluation_count}")

    total_prompt_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.prompt_tokens_used), 0))
        .join(models.Run)
        .filter(models.Run.batch_run_id == batch_id)
        .scalar()
    )
    logger.debug(f"Total prompt tokens for batch_id {batch_id}: {total_prompt_tokens}")

    total_generate_tokens = (
        db.query(func.coalesce(func.sum(models.Evaluation.generate_tokens_used), 0))
        .join(models.Run)
        .filter(models.Run.batch_run_id == batch_id)
        .scalar()
    )
    logger.debug(
        f"Total generate tokens for batch_id {batch_id}: {total_generate_tokens}"
    )

    stats = {
        "batch_id": batch.id,
        "name": batch.name,
        "run_count": run_count,
        "evaluation_count": evaluation_count,
        "total_prompt_tokens": total_prompt_tokens,
        "total_generate_tokens": total_generate_tokens,
    }
    logger.info(f"Batch stats for batch_id {batch_id}: {stats}")
    return stats


@router.post("/onboard", response_model=schemas.OnboardUserResponse)
def onboard_user(
    onboard_data: schemas.OnboardUserRequest, db: Session = Depends(get_db_gen)
):
    try:
        logger.debug(f"Onboarding user with data: {onboard_data}")
        # Extract the data from the payload
        engagement_id = onboard_data.engagement_id
        new_project_name = onboard_data.new_project_name
        new_user_email = onboard_data.new_user_email
        new_user_name = onboard_data.new_user_name
        project_id = onboard_data.project_id
        role_id = onboard_data.role_id
        user_id = onboard_data.user_id

        response_dict = {}

        # Validate the provided data
        if not engagement_id or not role_id or not (user_id or new_user_email):
            logger.error("Missing required fields for onboarding")
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Handle the creation of a new project if needed
        if new_project_name:
            logger.debug(f"Creating new project with name: {new_project_name}")
            project = models.Project(name=new_project_name, engagement_id=engagement_id)
            db.add(project)
            db.commit()
            db.refresh(project)
            project_id = project.id

        # Handle the creation of a new user if needed
        if new_user_email:
            logger.debug(f"Creating new user with email: {new_user_email}")
            user = models.User(name=new_user_name, email=new_user_email)
            db.add(user)
            db.commit()
            db.refresh(user)
            payload = {
                "user_email": new_user_email,
                "env": env_vars["ENVIRONMENT"],
                "user_id": user.id,
            }
            user.api_token = create_access_token(payload)
            db.add(user)
            user_id = user.id
            response_dict.update({"token": user.api_token})

        # Check if the association between user, project, and role already exists
        existing_association = (
            db.query(models.UserProjectRole)
            .filter_by(user_id=user_id, project_id=project_id, role_id=role_id)
            .first()
        )
        response_dict.update({"message": "existing"})
        # If the association does not exist, create it
        if not existing_association:
            logger.debug(
                f"Creating new association for user_id: {user_id}, project_id: {project_id}, role_id: {role_id}"
            )
            association = models.UserProjectRole(
                user_id=user_id, project_id=project_id, role_id=role_id
            )
            db.add(association)
            db.commit()
            response_dict.update({"message": "new"})

        response_dict.update({"status": "success"})
        logger.info(f"User onboarded successfully with data: {response_dict}")
        return response_dict
    except Exception as e:
        import traceback

        detail = traceback.format_exc()
        logger.error(f"Error during user onboarding: {detail}")
        raise HTTPException(status_code=500, detail=str(e))
