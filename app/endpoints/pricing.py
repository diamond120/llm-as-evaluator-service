from datetime import timedelta, date
import json
from sqlite3 import IntegrityError
from typing import Any, Dict, List, Optional
from app.db_api.models.models import (
    Engagement,
    Evaluator,
    LLMPricing,
    Evaluation,
    Project,
    Run,
    UserProjectRole,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, and_, or_, case
from sqlalchemy.orm import Session, load_only

from app.db_api import database
from app.logging_config import logger
from app.schemas.pricing import LLMPricingCreate, LLMPricingResponse, TokenUsageData
from common.utils import load_env

env_vars = load_env()


router = APIRouter()


@router.get("/", response_model=List[LLMPricingResponse])
def get_llm_pricing(
    skip: int = 0,
    limit: int = 100,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    version: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(database.get_db_gen),
):
    query = db.query(LLMPricing)

    if provider:
        query = query.filter(LLMPricing.provider == provider)
    if model:
        query = query.filter(LLMPricing.model == model)
    if version:
        query = query.filter(LLMPricing.version == version)
    if active_only:
        query = query.filter(LLMPricing.effective_to.is_(None))

    return (
        query.order_by(
            LLMPricing.provider,
            LLMPricing.model,
            LLMPricing.version,
            LLMPricing.effective_from.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/provider-models", response_model=Dict[str, List[str]])
def get_provider_models(db: Session = Depends(database.get_db_gen)):
    # Query to get distinct providers and models
    query = (
        db.query(LLMPricing.provider, LLMPricing.model)
        .distinct()
        .order_by(LLMPricing.provider, LLMPricing.model)
    )

    # Execute the query and fetch all results
    results = query.all()

    # Create a dictionary to store the provider-model mapping
    provider_models = {}

    # Populate the dictionary
    for provider, model in results:
        if provider not in provider_models:
            provider_models[provider] = []
        provider_models[provider].append(model)

    return provider_models


@router.post("/create/", response_model=LLMPricingResponse)
def create_llm_pricing(
    pricing: LLMPricingCreate, db: Session = Depends(database.get_db_gen)
):
    # Check if there's an existing active pricing for the same provider, model, and version
    existing_pricing = (
        db.query(LLMPricing)
        .filter(
            LLMPricing.provider == pricing.provider,
            LLMPricing.model == pricing.model,
            LLMPricing.version == pricing.version,
            LLMPricing.effective_to.is_(None),
        )
        .first()
    )

    if existing_pricing:
        # Update the effective_to date of the existing pricing
        existing_pricing.effective_to = pricing.effective_from - timedelta(days=1)

    # Create new pricing entry
    db_pricing = LLMPricing(**pricing.dict())
    db.add(db_pricing)

    try:
        db.commit()
        db.refresh(db_pricing)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid data or duplicate entry")

    return db_pricing


@router.get("/token-usage", response_model=List[TokenUsageData])
async def get_token_usage(
    engagement_id: str = Query(..., description="Engagement ID"),
    project_id: Optional[str] = Query(None, description="Project ID"),
    start: date = Query(..., description="Start date"),
    end: date = Query(..., description="End date"),
    db: Session = Depends(database.get_db_gen),
):
    # Subquery to get the latest pricing for each model
    latest_pricing = (
        db.query(
            LLMPricing.model,
            func.max(LLMPricing.effective_from).label("max_effective_from"),
        )
        .filter(LLMPricing.effective_from <= end)
        .group_by(LLMPricing.model)
        .subquery()
    )

    # Main query
    query = (
        db.query(
            func.date(Evaluation.created_at).label("date"),
            func.any_value(
                case(
                    (
                        Evaluation.evaluator_config_override.isnot(None),
                        func.json_unquote(
                            func.json_extract(
                                Evaluation.evaluator_config_override,
                                "$.llm_config.provider",
                            )
                        ),
                    ),
                    else_=Evaluator.llm_provider,
                )
            ).label("provider"),
            func.any_value(
                case(
                    (
                        Evaluation.evaluator_config_override.isnot(None),
                        func.json_unquote(
                            func.json_extract(
                                Evaluation.evaluator_config_override,
                                "$.llm_config.model",
                            )
                        ),
                    ),
                    else_=Evaluator.llm_model,
                )
            ).label("model"),
            func.sum(Evaluation.prompt_tokens_used).label("input_tokens"),
            func.sum(Evaluation.generate_tokens_used).label("output_tokens"),
            func.sum(
                case(
                    (
                        Evaluation.evaluator_config_override.isnot(None),
                        (
                            Evaluation.prompt_tokens_used
                            * LLMPricing.input_price_per_million_tokens
                            / 1000000
                        )
                        + (
                            Evaluation.generate_tokens_used
                            * LLMPricing.output_price_per_million_tokens
                            / 1000000
                        ),
                    ),
                    else_=(
                        Evaluation.prompt_tokens_used
                        * LLMPricing.input_price_per_million_tokens
                        / 1000000
                    )
                    + (
                        Evaluation.generate_tokens_used
                        * LLMPricing.output_price_per_million_tokens
                        / 1000000
                    ),
                )
            ).label("total_cost"),
        )
        .join(Evaluator, Evaluation.evaluator_id == Evaluator.id)
        .join(UserProjectRole, Evaluation.user_project_role_id == UserProjectRole.id)
        .join(Project, UserProjectRole.project_id == Project.id)
        .join(latest_pricing, latest_pricing.c.model == Evaluator.llm_model)
        .join(
            LLMPricing,
            and_(
                LLMPricing.model == latest_pricing.c.model,
                LLMPricing.effective_from == latest_pricing.c.max_effective_from,
            ),
        )
        .filter(
            Project.engagement_id == engagement_id,
            func.date(Evaluation.created_at).between(start, end),
        )
    )

    if project_id:
        query = query.filter(Project.id == project_id)

    evaluations = (
        query.group_by(func.date(Evaluation.created_at))
        .order_by(func.date(Evaluation.created_at))
        .all()
    )

    if not evaluations:
        raise HTTPException(
            status_code=404,
            detail="No data found for the specified parameters",
        )

    result = [
        TokenUsageData(
            date=row.date,
            provider=row.provider,
            model=row.model,
            inputTokens=row.input_tokens,
            outputTokens=row.output_tokens,
            totalCost=row.total_cost,
        )
        for row in evaluations
    ]

    return result
