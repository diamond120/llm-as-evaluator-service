import json
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_api import database, models
from app.logging_config import logger
from app.pydantic_models import WebhookRequest, WebhookResponse
from app.utils.auth import async_get_current_user, get_current_user
from workers.webhook_tasks import process_webhook_data
import datetime

router = APIRouter()


@router.post("/register", response_model=WebhookResponse)
async def register_webhook(
    req: WebhookRequest,
    user: models.User = Depends(async_get_current_user),
    db: Session = Depends(database.get_db_gen),
):
    """
    Endpoint to register a webhook for an engagement.
    - `req`: WebhookRequest containing the engagement name, callback URL, and token.
    - `user`: The current authenticated user.
    - `db`: Database session dependency.
    Returns a WebhookResponse with the engagement name and status of the registration.
    """

    status = "failed"  # Initialize the status as failed
    try:
        logger.info(req.engagement_name)  # Log the engagement name from the request
        engagement = (
            db.query(models.Engagement)
            .filter(models.Engagement.name == req.engagement_name)
            .first()
        )
        if engagement:
            engagement.webhook_url = req.callback_url  # Update the webhook URL
            engagement.auth_token = req.token  # Update the authentication token
            db.commit()  # Commit the changes to the database
            db.refresh(engagement)  # Refresh the engagement object
            status = "success"  # Update the status to success
    except Exception as ex:
        # Raise an HTTPException if an error occurs
        raise HTTPException(
            status_code=404,
            detail="Webhook is not registered",
        )
    return WebhookResponse(engagement_name=req.engagement_name, status=status)


@router.put("/{engagement_name}/", response_model=WebhookResponse)
async def update_webhook(
    req: WebhookRequest,
    engagement_name: str,
    user: models.User = Depends(async_get_current_user),
    db: Session = Depends(database.get_db_gen),
):
    """
    Endpoint to update a webhook for an engagement.
    - `req`: WebhookRequest containing the engagement name, callback URL, and token.
    - `engagement_name`: The name of the engagement to be updated.
    - `user`: The current authenticated user.
    - `db`: Database session dependency.
    Returns a WebhookResponse with the engagement name and status of the update.
    """

    status = "failed"  # Initialize the status as failed
    try:
        engagement = (
            db.query(models.Engagement)
            .filter(models.Engagement.name == req.engagement_name)
            .first()
        )
        if engagement:
            engagement.webhook_url = req.callback_url  # Update the webhook URL
            engagement.auth_token = req.token  # Update the authentication token
            db.commit()  # Commit the changes to the database
            db.refresh(engagement)  # Refresh the engagement object
            status = "success"  # Update the status to success
    except Exception as ex:
        # Raise an HTTPException if an error occurs
        raise HTTPException(
            status_code=404,
            detail="Data is not updated",
        )
    return WebhookResponse(engagement_name=req.engagement_name, status=status)
