import asyncio
from functools import partial
import json
from datetime import datetime

from celery import shared_task
from fastapi import HTTPException
import httpx

from app.db_api.database import get_db_ctx_manual
from app.db_api.models import models
from app.logging_config import logger

event_loop = None


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Asynchronous function to fetch data from a service with retry logic and exponential backoff
async def fetch_data_from_service(
    url: str,
    headers: dict,
    data: dict,
    timeout: float,
    retries: int,
    backoff_factor: float,
) -> dict:
    async with httpx.AsyncClient() as client:
        for attempt in range(retries):
            try:
                json_data = json.dumps(data, cls=DateTimeEncoder)
                logger.info(f"Posting data to URL: {url}")
                # logger.debug(f"Request data: {json_data}")
                response = await client.post(
                    url, headers=headers, content=json_data, timeout=timeout
                )
                logger.info(f"Response status: {response.status_code}")
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt == retries - 1:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Service request failed after {retries} retries: {str(exc)}",
                    )
                await asyncio.sleep(backoff_factor * (2**attempt))


# Asynchronous function to push data to an external tool (e.g., an LLM service)
async def push_to_llm_tool(
    service_url: str,
    headers: dict,
    data: dict,
    timeout: float = 5.0,
    retries: int = 3,
    backoff_factor: float = 2.0,
):
    if not headers:
        logger.info(f"Headers is not there in call back url for {service_url}")
        headers = {
            "Content-Type": "application/json",
        }
        headers = {k: v for k, v in headers.items() if v is not None}

    try:
        return await fetch_data_from_service(
            service_url, headers, data, timeout, retries, backoff_factor
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"Error calling webhook with data {data}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}")


def initialize_event_loop():
    """
    Initializes a persistent event loop for the worker process.
    """
    global event_loop
    if event_loop is None:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)


def run_async_task(async_func, *args, **kwargs):
    """
    Runs an asynchronous function in the persistent event loop.
    """
    initialize_event_loop()  # Ensure the event loop is initialized
    return event_loop.run_until_complete(async_func(*args, **kwargs))


@shared_task
def process_webhook_data(data):
    run_id = data.get("run", {}).get("run_id")
    if not run_id:
        logger.error("No run_id provided in webhook data")
        return

    status = data.get("run", {}).get("run_status")
    engagement_name = data.get("run", {}).get("engagement_name")
    run_evaluations = data.get("evaluations", [])

    evaluations = [
        eval for eval in run_evaluations if not eval.get("is_aggregator")
    ]
    aggregated_evaluations = [
        eval for eval in run_evaluations if eval.get("is_aggregator")
    ]

    callback = data.get("run", {}).get("callback", {})
    if not callback:
        return
    
    webhook_url = callback.get("url", None)
    headers = callback.get("headers", None)

    logger.info(f"Webhook url for run_id {run_id}: {webhook_url}")

    if not webhook_url:
        return
    
    response = {
        "run_id": run_id,
        "status": status,
        "evaluations": evaluations,
        "aggregated_evaluations": aggregated_evaluations,
    }

    logger.info(f"Evaluations: {evaluations}")
    logger.info(f"Aggregated Evaluations: {aggregated_evaluations}")
    if status == "failure":
        response.update(
            {
                "traceback": data.get("traceback"),
                "status": "failed",
            }
        )

    logger.info(f"Push to llm with data: {response}")
    # Use the run_async_task function to handle asynchronous tasks
    run_async_task(push_to_llm_tool, webhook_url, headers, response)