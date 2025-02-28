import asyncio
import hashlib
import json
import time

import redis
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db_api import database, models
from app.logging_config import logger
from app.pydantic_models import (
    BatchRunRequest,
    BatchRunResponse,
    BatchRunStatusResponse,
    EvaluationResponse,
    RunResponse,
    RunStatusResponse,
)
from app.utils.auth import async_get_current_user, get_current_user
from app.utils.cache_manager import RequestCacheManager
from app.utils.query import async_get_user_project_object
from common.utils import load_env, get_next_queue
from workers import slim_tasks
from workers.slim_tasks import RunStatus

env_vars = load_env()
PROJECT_ID = env_vars["GOOGLE_CLOUD_PROJECT"]
TOPIC_ID = env_vars["PUBSUB_TOPIC"]
DEFAULT_EMAIL = "admintest@xxxx.com"
MAX_WAIT_TIME_SYNC_REQUEST = int(env_vars.get("MAX_WAIT_TIME_SYNC_REQUEST", 120))
router = APIRouter()

RATE_LIMIT = int(env_vars.get("RATE_LIMIT", 500))  # requests
TIME_WINDOW = int(env_vars.get("TIME_WINDOW", 60))  # seconds (1 minute)

RATE_LIMITER_ENABLED = env_vars.get("RATE_LIMITER_ENABLED", "f").lower() in (
    "true",
    "1",
    "t",
)

# Cache configuration from environment variables
CACHE_ENABLED = env_vars.get("CACHE_ENABLED", "false").lower() in ("true", "1", "t")
CACHE_TTL = int(env_vars.get("CACHE_TTL", "900"))  # Default 15 mins
CACHE_PREFIX = env_vars.get("CACHE_PREFIX", "run_cache")

redis_host = env_vars.get("REDIS_HOST", "localhost")
redis_port = int(env_vars.get("REDIS_PORT", 6379))
redis_db = int(env_vars.get("REDIS_DB", 0))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)

def rate_limiter(engagement_name: str):
    key = f"rate_limit:{engagement_name}"

    # Increment the request count and set expiry if it's the first request
    request_count = redis_client.incr(key)
    if request_count == 1:
        redis_client.expire(key, TIME_WINDOW)

    if request_count > RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many requests for this engagement. Please try after 1 minute.",
        )


async def async_create_batch_and_runs(req: BatchRunRequest, user=None, db=None) -> dict:
    sss = time.time()
    res = {"runs": []}

    try:
        start_time = time.time()
        user_project_obj, project, engagment, user = (
            await async_get_user_project_object(
                db,
                req.engagement_name,
                req.project_name,
                user.email if user else DEFAULT_EMAIL,
                create_project_if_not=req.should_create_project,
            )
        )
        elapsed_time = time.time() - start_time
        logger.info(
            f"Time taken to get user project object: {elapsed_time:.4f} seconds"
        )
        sss = time.time()
        # user_project_obj = user_project_obj[0]
        user_project_obj_id = await user_project_obj.awaitable_attrs.id

        new_batch_run = models.BatchRun(
            name=req.batch_name,
            user_project_role_id=user_project_obj.id,
        )
        logger.debug(f"New batch run details: {new_batch_run.__dict__}")
        db.add(new_batch_run)

        res["batch_run_created_at"] = new_batch_run.created_at
        res["batch_run_updated_at"] = new_batch_run.updated_at
        # await project.awaitable_attrs.id
        # res["engagement_id"] = project.engagement_id
        # res["project_name"] = project.name
        logger.info(f"Batch created in {time.time() - sss:.4f} seconds")
        sss = time.time()
        evaluation_names = [eval_request.name for eval_request in req.evaluations]
        if req.aggregated_evaluations:
            evaluation_names += [
                eval_request.name for eval_request in req.aggregated_evaluations
            ]
        if len(evaluation_names) != len(set(evaluation_names)):
            raise HTTPException(
                status_code=400,
                detail="Evaluation names must be unique across evaluations and aggregated evaluations.",
            )
        logger.debug("Before creating run dict")

        async def create_run_dict(new_run, input_item):
            return {
                "run_id": await new_run.awaitable_attrs.id,
                "run_status": new_run.status,
                "input": input_item,
                "input_type": req.input_type,
                "batch_run_id": res["batch_run_id"],
                "is_dev_request": req.is_dev_request,
                "user_project_role_id": user_project_obj_id,
                "parse": req.parse,
                "format_to_issues_scores": req.format_to_issues_scores,
                "engagement_name": req.engagement_name,
                "callback": req.callback,
            }

        def create_new_run(input_item, store_input):
            input_data_json = json.dumps(input_item, sort_keys=True)
            input_data_hash = hashlib.sha256(
                (input_data_json + str(req.input_type)).encode("utf-8")
            ).hexdigest()

            return models.Run(
                user_project_role_id=user_project_obj_id,
                batch_run=new_batch_run,
                status=RunStatus.PENDING.value,
                item_metadata=req.item_metadata,
                input_hash=input_data_hash,
                stage1_left=len(req.evaluations),
                stage2_left=(
                    len(req.aggregated_evaluations) if req.aggregated_evaluations else 0
                ),
                message=input_data_json if store_input else None,
            )

        logger.debug("Creating new runs")
        new_runs = [create_new_run(item, req.store_input) for item in req.inputs]
        logger.debug("Adding new runs to the database")
        db.add_all(new_runs)
        await db.flush()
        await db.commit()
        res["batch_run_id"] = await new_batch_run.awaitable_attrs.id
        logger.info(f"New batch run created with ID: {new_batch_run.id}")
        results = [
            await create_run_dict(new_run, input_item)
            for new_run, input_item in zip(new_runs, req.inputs)
        ]
    except Exception as e:
        await db.rollback()
        logger.error("Error creating batch and runs", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))
    if any(result is None for result in results):
        raise HTTPException(status_code=404, detail="One or more results are not found")

    res["runs"].extend(results)
    logger.info(f"Runs created in {time.time() - sss:.4f} seconds")
    return res


async def wait_for_celery_result_task_id(task_id: str, depth=0):
    max_wait_time = MAX_WAIT_TIME_SYNC_REQUEST
    start_time = time.time()

    while True:
        result = AsyncResult(task_id)
        if result.ready() and not result.failed():
            r = result.result
            if depth == 0:
                return r
            else:
                return await wait_for_celery_result_task_id(r, depth - 1)
        elif result.failed():
            raise

        if time.time() - start_time > max_wait_time:
            raise TimeoutError(
                f"Max wait time of 10 minutes exceeded for task_id: {task_id}"
            )

        await asyncio.sleep(0.5)


async def wait_for_celery_result(task_id: str):
    while True:
        result = AsyncResult(task_id)
        if result.ready() and not result.failed():
            r = result.result
            return await wait_for_celery_result2(r[0][0])
        elif result.failed():
            raise
        await asyncio.sleep(0.3)


async def wait_for_celery_result2(task_id: str):
    while True:
        result = AsyncResult(task_id)
        if result.ready() and not result.failed():
            r = result.result
            return await wait_for_celery_result3(r[0][0])
        elif result.failed():
            raise
        await asyncio.sleep(0.3)


async def wait_for_celery_result3(task_id: str):
    max_wait_time = 600  # 10 minutes in seconds
    start_time = time.time()

    while True:
        result = AsyncResult(task_id)
        if result.ready() and not result.failed():
            r = result.result
            return r
        elif result.failed():
            raise

        if time.time() - start_time > max_wait_time:
            raise TimeoutError(
                "Max wait time of 10 minutes exceeded for task_id: {}".format(task_id)
            )

        await asyncio.sleep(0.3)


async def gather_celery_results(tasks):
    awaitables = [wait_for_celery_result_task_id(task.id, depth=2) for task in tasks]
    return await asyncio.gather(*awaitables)


async def initiate_run_common(req, user, db, is_async, is_bulk_request=False):
    """Common logic for initiating a run."""
    all_runs = []
    try:
        start_time = time.time()
        all_runs_dict = await async_create_batch_and_runs(req, user, db=db)
        end_time = time.time()
        logger.info(
            f"Execution time create_batch_and_runs: {end_time - start_time} seconds"
        )
    except Exception as e:
        logger.error("Error initiating run", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

    runs_tasks = []
    try:
        for run_item in all_runs_dict["runs"]:
            all_runs.append(
                {"run_id": run_item["run_id"], "status": run_item["run_status"]}
            )
            if is_bulk_request:
                # Send data to Redis queue in FIFO order
                print(f"Send to slow queue for run_id {run_item['run_id']}")
                redis_payload = {
                    "run_item": run_item,
                    "evaluations": [e.model_dump() for e in req.evaluations],
                    "aggregated_evaluations": (
                        [e.model_dump() for e in req.aggregated_evaluations]
                        if req.aggregated_evaluations is not None
                        else None
                    ),
                }
                redis_client.rpush("bulk_batch_request", json.dumps(redis_payload))
            else:
                print(f"Directly sending to process_run for run_id {run_item['run_id']}")
                runs_task = slim_tasks.process_run.apply_async(
                    args=[
                        run_item,
                        [e.model_dump() for e in req.evaluations],
                        (
                            [e.model_dump() for e in req.aggregated_evaluations]
                            if req.aggregated_evaluations is not None
                            else None
                        ),
                    ],
                    queue=get_next_queue("process_queue", is_bulk_request),
                    kwargs={"save_to_db": True},
                )
                runs_tasks.append(runs_task)
                logger.debug("Started processing run at time: %s", time.time())
    except Exception as e:
        logger.error("Error processing run", exc_info=e)
        raise HTTPException(status_code=500, detail=str(e))

    if is_async:
        return all_runs_dict, all_runs, runs_tasks

    return all_runs_dict, all_runs, runs_tasks


async def process_sync_results(runs_tasks, all_runs_dict, req):
    """Process synchronous results."""
    try:
        runs_results = await gather_celery_results(runs_tasks)
    except Exception as e:
        logger.error("Error gathering celery results", exc_info=e)
        raise HTTPException(
            status_code=500, detail="Failed to gather evaluations results"
        )

    saved_runs = []
    for run_result in runs_results:
        changed_run_fields = run_result["run_fields"]
        run = run_result["run"]
        evaluations = run_result["evaluations"]

        stage1 = [
            EvaluationResponse(
                evaluator_id=evaluation.get("evaluator_id"),
                name=evaluation["name"],
                status=evaluation["status"],
                fail_reason=evaluation["fail_reason"],
                output=evaluation["output"],
                is_used_for_aggregation=evaluation["is_used_for_aggregation"],
            )
            for evaluation in evaluations
            if not evaluation["is_aggregator"]
        ]
        stage2 = [
            EvaluationResponse(
                evaluator_id=evaluation.get("evaluator_id"),
                name=evaluation["name"],
                status=evaluation["status"],
                fail_reason=evaluation["fail_reason"],
                output=evaluation["output"],
                is_used_for_aggregation=evaluation["is_used_for_aggregation"],
            )
            for evaluation in evaluations
            if evaluation["is_aggregator"]
        ]
        r = RunResponse(
            created_at="NOT_PROVIDED",
            updated_at="NOT_PROVIDED",
            evaluations_failed=changed_run_fields["stage1_failed"],
            aggregated_evaluations_failed=changed_run_fields["stage2_failed"],
            # engagement_id=all_runs_dict["engagement_id"],
            # project_name=all_runs_dict["project_name"],
            run_id=run["run_id"],
            status=changed_run_fields["status"],
            item_metadata=req.item_metadata,
            evaluations=stage1,
            aggregated_evaluations=stage2,
        )
        saved_runs.append(r)
    return saved_runs


async def get_run_response(run_orm):
    # Assuming run_orm is already loaded
    user_project_role = await run_orm.awaitable_attrs.user_project_role
    project = await user_project_role.awaitable_attrs.project
    engagement = await project.awaitable_attrs.engagement

    # Asynchronously load evaluations
    evaluations = await asyncio.gather(
        *[
            async_get_evaluation_response(evaluation)
            for evaluation in run_orm.evaluations
            if not evaluation.is_aggregator
        ]
    )
    aggregated_evaluations = await asyncio.gather(
        *[
            async_get_evaluation_response(evaluation)
            for evaluation in run_orm.evaluations
            if evaluation.is_aggregator
        ]
    )
    logger.info(f"Run status: {run_orm.status}, Run ID: {run_orm.id}")
    return RunResponse(
        created_at=run_orm.created_at,
        updated_at=run_orm.updated_at,
        evaluations_failed=run_orm.stage1_failed,
        aggregated_evaluations_failed=run_orm.stage2_failed,
        engagement_id=engagement.id,
        project_name=project.name,
        run_id=run_orm.id,
        status=run_orm.status,
        item_metadata=run_orm.item_metadata,
        evaluations=evaluations,
        aggregated_evaluations=aggregated_evaluations,
    )


async def async_get_evaluation_response(evaluation):
    return EvaluationResponse(
        evaluator_id=evaluation.evaluator_id,
        name=evaluation.name,
        status=evaluation.status,
        fail_reason=evaluation.fail_reason,
        output=evaluation.output,
        is_used_for_aggregation=evaluation.is_used_for_aggregation,
    )


async def start_evaluation_run(req, user, db, is_bulk_request):
    """Initiate a run with multiple evaluations for a single input."""
    log_payload = req.model_dump_json(exclude={"inputs"})
    logger.debug(f"Received request payload: {log_payload}")
    start_time = time.time()

    logger.debug(f"is bulk request {is_bulk_request}")

    if RATE_LIMITER_ENABLED:
        rate_limiter(req.engagement_name)

    cached_run_id = None
    if CACHE_ENABLED:
        logger.debug("Cache is enabled, checking for existing run")
        # Initialize cache manager
        cache_manager = RequestCacheManager(redis_client)

        # Construct cache key from request
        cache_key = cache_manager.construct_cache_key(req.model_dump())

        # Check cache for existing run
        if cache_key:
            cached_run_id = await cache_manager.get_cached_run_id(cache_key)
            if cached_run_id:
                logger.info(f"Found cached run_id: {cached_run_id}, retrieving status")
                # Retrieve the existing run status
                query = (
                    select(models.Run)
                    .options(joinedload(models.Run.batch_run))
                    .filter(models.Run.id == cached_run_id)
                )
                result = await db.execute(query)
                existing_run = result.unique().scalar_one_or_none()

                if existing_run:
                    return BatchRunStatusResponse(
                        batch_run_id=existing_run.batch_run.id,
                        created_at=str(existing_run.batch_run.created_at),
                        updated_at=str(existing_run.batch_run.updated_at),
                        runs=[
                            {"run_id": existing_run.id, "status": existing_run.status}
                        ],
                        is_batch_ready=existing_run.status
                        not in [RunStatus.PENDING.value, RunStatus.IN_PROGRESS.value],
                        runs_left=(
                            1
                            if existing_run.status
                            in [RunStatus.PENDING.value, RunStatus.IN_PROGRESS.value]
                            else 0
                        ),
                    )

    # If no cache hit or caching is disabled, proceed with normal execution
    all_runs_dict, all_runs, _ = await initiate_run_common(req, user, db, is_async=True, is_bulk_request=is_bulk_request)

    if CACHE_ENABLED and cache_key and all_runs:
        first_run_id = all_runs[0]["run_id"]
        cache_manager.cache_run_id(cache_key, first_run_id)
        logger.info(f"Cached new run_id: {first_run_id}")

    r = BatchRunStatusResponse(
        batch_run_id=all_runs_dict["batch_run_id"],
        created_at=str(all_runs_dict["batch_run_created_at"]),
        updated_at=str(all_runs_dict["batch_run_updated_at"]),
        # engagement_name=req.engagement_name,
        # project_name=req.project_name,
        runs=all_runs,
        is_batch_ready=False,
        runs_left=len(all_runs),
    )
    logger.info(
        f"Async run initiation completed in {time.time() - start_time:.4f} seconds"
    )
    return r
    


############# Routes #################################


@router.post("/sync", response_model=BatchRunResponse)
async def sync_initiate_run(
    req: BatchRunRequest,
    user: models.User = Depends(async_get_current_user),
    db=Depends(database.async_get_db_session),
):
    """Initiate a run with multiple evaluations for a single input."""
    all_runs_dict, _, runs_tasks = await initiate_run_common(
        req, user, db, is_async=False, is_bulk_request=False
    )
    saved_runs = await process_sync_results(runs_tasks, all_runs_dict, req)
    return BatchRunResponse(
        batch_run_id=all_runs_dict["batch_run_id"],
        created_at=str(all_runs_dict["batch_run_created_at"]),
        updated_at=str(all_runs_dict["batch_run_updated_at"]),
        runs=saved_runs,
    )


@router.post("", response_model=BatchRunStatusResponse)
@router.post("/", response_model=BatchRunStatusResponse)
async def async_initiate_run(
    req: BatchRunRequest,
    user: models.User = Depends(async_get_current_user),
    db=Depends(database.async_get_db_session),
):
    return await start_evaluation_run(req, user, db, is_bulk_request=False)


@router.post("bulk_batch_runs", response_model=BatchRunStatusResponse)
@router.post("/bulk_batch_runs", response_model=BatchRunStatusResponse)
async def async_bulk_batch_initiate_run(
    req: BatchRunRequest,
    user: models.User = Depends(async_get_current_user),
    db=Depends(database.async_get_db_session),
):
    return await start_evaluation_run(req, user, db, is_bulk_request=True)


@router.get("/{run_id}/status/", response_model=RunStatusResponse)
@router.get("/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id: int,
    user: models.User = Depends(async_get_current_user),
    db: AsyncSession = Depends(database.async_get_db_session),
):
    """Get a small status object to see if the evaluations are complete."""
    query = (
        select(models.Run)
        .options(
            joinedload(models.Run.user_project_role)
            .joinedload(models.UserProjectRole.project)
            .joinedload(models.Project.engagement)
        )
        .filter(models.Run.id == run_id)
    )

    result = await db.execute(query)
    db_run = result.unique().scalar_one_or_none()

    if db_run is None:
        logger.error(f"Run with ID {run_id} not found")
        raise HTTPException(status_code=404, detail="Run not found")

    logger.debug(f"Retrieved status for run_id {run_id}")
    return RunStatusResponse(
        created_at=db_run.created_at,
        updated_at=db_run.updated_at,
        engagement_id=db_run.user_project_role.project.engagement.id,
        project_name=db_run.user_project_role.project.name,
        run_id=db_run.id,
        status=db_run.status,
    )


@router.get("/batch/{batch_run_id}/status/", response_model=BatchRunStatusResponse)
@router.get("/batch/{batch_run_id}/status", response_model=BatchRunStatusResponse)
async def batch_status(
    batch_run_id: int,
    db: AsyncSession = Depends(database.async_get_db_session),
    user: models.User = Depends(async_get_current_user),
):
    """Retrieve the status of a batch run with multiple evaluations."""
    query = (
        select(models.BatchRun)
        .options(
            joinedload(models.BatchRun.user_project_role)
            .joinedload(models.UserProjectRole.project)
            .joinedload(models.Project.engagement),
            joinedload(models.BatchRun.runs),
        )
        .filter(models.BatchRun.id == batch_run_id)
    )

    result = await db.execute(query)
    batch_run = result.unique().scalar_one_or_none()

    if batch_run is None:
        logger.error(f"Batch run with ID {batch_run_id} not found")
        raise HTTPException(status_code=404, detail="Batch run not found")

    run_statuses = [{"run_id": run.id, "status": run.status} for run in batch_run.runs]
    runs_left = sum(
        1
        for run in run_statuses
        if run["status"] in (RunStatus.PENDING.value, RunStatus.IN_PROGRESS.value)
    )
    is_batch_ready = runs_left == 0

    return BatchRunStatusResponse(
        batch_run_id=batch_run.id,
        created_at=batch_run.created_at,
        updated_at=batch_run.updated_at,
        engagement_name=batch_run.user_project_role.project.engagement.name,
        project_name=batch_run.user_project_role.project.name,
        runs=run_statuses,
        is_batch_ready=is_batch_ready,
        runs_left=runs_left,
    )


@router.get("/batch/{batch_run_id}/", response_model=BatchRunResponse)
@router.get("/batch/{batch_run_id}", response_model=BatchRunResponse)
async def get_batch_run(
    batch_run_id: int,
    db: AsyncSession = Depends(database.async_get_db_session),
    user: models.User = Depends(async_get_current_user),
):
    """Retrieve details for a specific batch run."""
    batch_run = await db.execute(
        select(models.BatchRun).filter(models.BatchRun.id == batch_run_id)
    )
    batch_run = batch_run.scalar_one_or_none()
    if batch_run is None:
        logger.error(f"Batch run with ID {batch_run_id} not found")
        raise HTTPException(status_code=404, detail="Batch run not found")

    runs = await db.execute(
        select(models.Run)
        .options(selectinload(models.Run.evaluations))
        .filter(models.Run.batch_run_id == batch_run_id)
    )
    runs = runs.scalars().all()
    run_responses = []
    for run in runs:
        run_responses.append(await get_run_response(run))

    return BatchRunResponse(
        batch_run_id=batch_run.id,
        created_at=batch_run.created_at,
        updated_at=batch_run.updated_at,
        runs=run_responses,
    )


@router.get("/{run_id}/", response_model=RunResponse)
@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(database.async_get_db_session),
    user: models.User = Depends(async_get_current_user),
):
    """
    Retrieve full run details including item metadata, evaluation results, and aggregated evaluation results in addition to the run status object.
    """
    db_run = await db.execute(
        select(models.Run)
        .options(selectinload(models.Run.evaluations))
        .filter(models.Run.id == run_id)
    )
    db_run = db_run.scalar_one_or_none()
    if db_run is None:
        logger.error(f"Run with ID {run_id} not found")
        raise HTTPException(status_code=404, detail="Run not found")
    return await get_run_response(db_run)


@router.get(
    "/uuiasfhuashFUSAU&93klafskljasFGY34ijrt2398jashfua/health-test-evaluator",
    response_model=RunResponse,
)
async def health_test_eval(
    poll_interval: int = 5,  # seconds between each poll
    timeout: int = 120,  # total timeout for the entire process
):
    """Initiate a run, poll its status, and return the final result within a 120s limit."""
    start_time = time.time()

    async with database.async_get_db_session_ctx() as session:
        user_result = await session.execute(
            select(models.User).filter(
                models.User.email == "health-test-eval@xxxx.com"
            )
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            logger.error("User with ID 5 not found")
            raise HTTPException(status_code=404, detail="User not found")

    # Construct the BatchRunRequest
    req = BatchRunRequest(
        batch_name="health-test-eval-batch",
        engagement_name="health-test",
        project_name="health-test",
        item_metadata={},
        input_type="parsed_json_args",
        inputs=[{}],
        evaluations=[
            {
                "evaluator_name": "health-test-evaluator",
                "name": "health-test-eval",
                "use_for_agg_layer": False,
                "config": {"payload": "STATUS_OK"},
            }
        ],
        aggregated_evaluations=[],
        parse=True,
        format_to_issues_scores=False,
        is_dev_request=False,
        force_skip_cache=True,
    )

    # Step 1: Initiate the run
    async with database.async_get_db_session_ctx() as session:
        batch_run_response = await async_initiate_run(req, user, session)
        run_id = batch_run_response.runs[0].run_id

    # Step 2: Poll the status of the batch run until completion or timeout
    while True:
        # Check if we have exceeded the total timeout
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            raise HTTPException(
                status_code=408, detail=f"Operation timed out after {timeout} seconds"
            )

        # Poll the status of the batch run
        async with database.async_get_db_session_ctx() as session:
            run = await get_run_status(run_id, user, session)
            # Check if all runs are complete
            if run.status.value not in [
                RunStatus.PENDING.value,
                RunStatus.IN_PROGRESS.value,
            ]:
                break

        # Wait for the next poll
        await asyncio.sleep(poll_interval)

    # Step 3: Retrieve and return the final result of the batch run
    # Ensure we have not exceeded the total timeout
    if time.time() - start_time > timeout:
        raise HTTPException(
            status_code=408, detail=f"Operation timed out after {timeout} seconds"
        )

    async with database.async_get_db_session_ctx() as session:
        return await get_run(run_id, session, user)
