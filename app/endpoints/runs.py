import hashlib
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.db_api import database, models
from app.db_api.database import get_db_ctx, get_db_ctx_manual
from app.logging_config import logger
from app.pydantic_models import (
    BatchRunRequest,
    BatchRunRequestNoEvaluator,
    BatchRunResponse,
    BatchRunStatusResponse,
    EvaluationRequest,
    EvaluationResponse,
    RunResponse,
    RunStatusResponse,
    SubmitPubsubMessagesAgainRequest,
)
from app.utils.auth import get_current_user
from app.utils.query import get_user_project_object
from common.pubsub_queue import (
    EvaluationStatus,
    RunStatus,
    create_stage_pubsub_messages,
    publish_messages,
)
from common.utils import load_env

env_vars = load_env()
PROJECT_ID = env_vars["GOOGLE_CLOUD_PROJECT"]
TOPIC_ID = env_vars["PUBSUB_TOPIC"]
DEFAULT_EMAIL = "admintest@xxxx.com"

router = APIRouter()


# Create Evaluation objects associated with the Run
def create_evaluations(
    evaluation_requests,
    is_aggregator,
    db,
    new_run_id,
    status,
    batch_run_id,
    user_proj_role_id,
    is_dev_request=False,
):
    """
    Create Evaluation objects for each evaluation request and store them in the database.

    Args:
        evaluation_requests (list): A list of EvaluationRequest objects containing evaluation details.
        is_aggregator (bool): Flag indicating if the evaluations are for aggregation.
        db (Session): Database session to be used for operations.
        new_run_id (int): The ID of the run these evaluations are associated with.
        status (Enum): The initial status of the evaluations.
        batch_run_id (int): The ID of the batch run these evaluations are associated with.
        user_proj_role_id (int): The ID of the user project role associated with these evaluations.

    Returns:
        list: A list of IDs for the newly created Evaluation objects.
    """
    logger.debug("Starting to create evaluations")
    evaluation_ids = []
    evaluator_names = {
        eval_request.evaluator_name
        for eval_request in evaluation_requests
        if not eval_request.evaluator_id
    }

    evaluators = (
        db.query(models.Evaluator)
        .filter(models.Evaluator.name.in_(evaluator_names))
        .all()
    )
    evaluator_dict = {evaluator.name: evaluator.id for evaluator in evaluators}
    new_evaluations = []
    logger.debug("Adding evaluations")
    for eval_request in evaluation_requests:
        config_override = None
        if is_dev_request:
            config_override = eval_request.evaluator_config_override.dict()
        evaluator_id = eval_request.evaluator_id
        if not evaluator_id:
            evaluator_id = evaluator_dict.get(eval_request.evaluator_name)
            if evaluator_id is None and not is_dev_request:
                logger.error(
                    f"Evaluator with name {eval_request.evaluator_name} not found"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Evaluator with name {eval_request.evaluator_name} not found",
                )
        logger.debug(f"Using evaluator_id: {evaluator_id}")
        new_evaluation = models.Evaluation(
            batch_run_id=batch_run_id,
            run_id=new_run_id,
            user_project_role_id=user_proj_role_id,
            evaluator_id=evaluator_id,
            name=eval_request.name,
            status=status.value,
            config=eval_request.config,
            is_used_for_aggregation=eval_request.use_for_agg_layer,
            is_aggregator=is_aggregator,
            evaluator_config_override=config_override,
            is_dev=is_dev_request,
        )
        new_evaluations.append(new_evaluation)

        db.add(new_evaluation)

    db.commit()
    logger.debug("Committed new evaluations to the database")
    # Gather uuid_token field from new evaluations
    uuid_tokens = [evaluation.uuid_token for evaluation in new_evaluations]

    # Search for these uuid_tokens in the database and get their IDs
    existing_evaluations = (
        db.query(models.Evaluation)
        .filter(models.Evaluation.uuid_token.in_(uuid_tokens))
        .all()
    )
    evaluation_ids = [evaluation.id for evaluation in existing_evaluations]

    logger.debug(f"Created evaluation IDs: {evaluation_ids}")
    return evaluation_ids


def bulk_insert(sess, cls, objects):
    # DOES NOT WORK WITH MYSQL THAT WE USE, NO RETURNING OR KEEP ORDER
    # creating objects beforehand to still have defaults filled
    data = [
        {k: v for k, v in obj.__dict__.items() if not k.startswith("_sa")}
        for obj in objects
    ]
    user_ids = sess.scalars(
        # insert(cls).returning(cls.id, sort_by_parameter_order=False), data
        insert(cls),
        data,
    )
    for user_id, input_object in zip(user_ids, objects):
        input_object.id = user_id
    return objects


# Function to create and add run object and evaluations to the database
def create_run_and_evaluations(req: BatchRunRequest, user=None) -> dict:
    logger.debug("Starting create_run_and_evaluations function")
    res = {"runs": []}
    with get_db_ctx_manual() as db:
        logger.debug("Fetching user project object")
        user_project_obj, project, user, engagement = get_user_project_object(
            db,
            req.engagement_name,
            req.project_name,
            user.email if user else DEFAULT_EMAIL,
            create_project_if_not=req.should_create_project,
        )
        user_project_obj_id = user_project_obj.id

        logger.debug("Creating new batch run")
        new_batch_run = models.BatchRun(
            name=req.batch_name,
            input_type=req.input_type,
            inputs=req.inputs,
            user_project_role_id=user_project_obj.id,
        )
        try:
            db.add(new_batch_run)
            db.commit()
            db.refresh(new_batch_run)
            new_batch_run_id = new_batch_run.id
            res["batch_run_id"] = new_batch_run.id
            res["batch_run_created_at"] = new_batch_run.created_at
            res["batch_run_updated_at"] = new_batch_run.updated_at
            logger.debug(f"New batch run created with ID: {new_batch_run_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating new batch run: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    logger.debug("Checking for unique evaluation names")
    evaluation_names = [eval_request.name for eval_request in req.evaluations]
    if req.aggregated_evaluations:
        evaluation_names += [
            eval_request.name for eval_request in req.aggregated_evaluations
        ]
    if len(evaluation_names) != len(set(evaluation_names)):
        logger.error(
            "Evaluation names must be unique across evaluations and aggregated evaluations."
        )
        raise HTTPException(
            status_code=400,
            detail="Evaluation names must be unique across evaluations and aggregated evaluations.",
        )

    # Create a new Run object

    def process_input_item(input_item, store_input):
        with get_db_ctx_manual() as db:
            try:
                input_data_json = json.dumps(input_item, sort_keys=True)
                input_data_hash = hashlib.sha256(
                    (input_data_json + str(req.input_type)).encode("utf-8")
                ).hexdigest()

                new_run = models.Run(
                    user_project_role_id=user_project_obj_id,
                    batch_run_id=new_batch_run_id,
                    status=RunStatus.PENDING.value,
                    item_metadata=req.item_metadata,
                    input_hash=input_data_hash,
                    stage1_left=len(req.evaluations),
                    stage2_left=(
                        len(req.aggregated_evaluations)
                        if req.aggregated_evaluations
                        else 0
                    ),
                    message=input_data_json if store_input else None,
                )
                db.add(new_run)
                db.commit()
                db.refresh(new_run)
                logger.debug(f"New run created with ID: {new_run.id}")

                stage1_eval_ids = create_evaluations(
                    req.evaluations,
                    False,
                    db,
                    new_run.id,
                    EvaluationStatus.QUEUED,
                    new_batch_run_id,
                    user_project_obj_id,
                    is_dev_request=req.is_dev_request,
                )
                stage2_eval_ids = None
                if req.aggregated_evaluations:
                    stage2_eval_ids = create_evaluations(
                        req.aggregated_evaluations,
                        True,
                        db,
                        new_run.id,
                        RunStatus.PENDING,
                        new_batch_run_id,
                        user_project_obj_id,
                        is_dev_request=req.is_dev_request,
                    )
                db.commit()
                logger.debug(f"Run {new_run.id} processed successfully")
                return {
                    "run_id": new_run.id,
                    "run_status": new_run.status,
                    "stage1_eval_ids": stage1_eval_ids,
                    "stage2_eval_ids": stage2_eval_ids,
                    "input": input_item,
                    "input_type": req.input_type,
                }
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing input item: {str(e)}")
                traceback.print_exc()

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(
                lambda item: process_input_item(item, req.store_input), req.inputs
            )
        )

    if any(result is None for result in results):
        logger.error("One or more results are not found")
        raise HTTPException(status_code=404, detail="One or more results are not found")

    res["runs"].extend(results)
    logger.debug("Finished create_run_and_evaluations function")
    return res


# Endpoint to initiate a run and create evaluations


@router.post("", response_model=BatchRunStatusResponse)
@router.post("/", response_model=BatchRunStatusResponse)
def initiate_run(
    req: BatchRunRequest,
    user: models.User = Depends(get_current_user),
):
    """Initiate a run with multiple evaluations for a single input."""
    all_runs = []
    try:
        logger.debug(f"User {user}")
        all_runs_dict = create_run_and_evaluations(req, user)
        logger.debug("Created run and evaluations successfully")
    except Exception as e:
        logger.exception(f"Error in creating run and evaluations: {e}")
        raise HTTPException(status_code=500, detail=str(traceback.format_exc()))

    try:
        for run_item in all_runs_dict["runs"]:
            stage1_messages = create_stage_pubsub_messages(
                evaluation_ids=run_item["stage1_eval_ids"],
                input_data=run_item["input"],
                input_type=run_item["input_type"],
                stage2_eval_ids=run_item["stage2_eval_ids"],
                parse=req.parse,
                is_dev=req.is_dev_request,
                format_to_issues_scores=req.format_to_issues_scores,
            )
            logger.debug(f"Created stage1 messages for run_id {run_item['run_id']}")
            publish_messages(stage1_messages)
            logger.debug(f"Published messages for run_id {run_item['run_id']}")
            all_runs.append(
                {"run_id": run_item["run_id"], "status": run_item["run_status"]}
            )
        logger.debug("Completed processing all runs")
    except Exception as e:
        logger.exception("Error in processing runs")
        raise HTTPException(status_code=500, detail=str(traceback.format_exc()))

    return BatchRunStatusResponse(
        batch_run_id=all_runs_dict["batch_run_id"],
        created_at=str(all_runs_dict["batch_run_created_at"]),
        updated_at=str(all_runs_dict["batch_run_updated_at"]),
        engagement_name=req.engagement_name,
        project_name=req.project_name,
        runs=all_runs,
        is_batch_ready=False,
        runs_left=len(all_runs),
    )


@router.post("/re-publish", response_model=RunStatusResponse)
def submit_pubsub_messages_again(
    req: SubmitPubsubMessagesAgainRequest, user: models.User = Depends(get_current_user)
):
    """Submit the pubsub messages again for a specific run."""
    try:
        with get_db_ctx() as db:
            run = db.query(models.Run).filter(models.Run.id == req.run_id).first()
            if not run:
                logger.error(f"Run with ID {req.run_id} not found")
                raise HTTPException(
                    status_code=404, detail=f"Run with ID {req.run_id} not found"
                )

            if not run.message:
                logger.error(f"Run with ID {req.run_id} Input is not saved in db")
                raise HTTPException(
                    status_code=404,
                    detail=f"Run with ID {req.run_id} Input is not saved in db",
                )

            stage1_messages = create_stage_pubsub_messages(
                [eval.id for eval in run.evaluations if not eval.is_aggregator],
                run.message,
                req.input_type,
                stage2_eval_ids=[
                    eval.id for eval in run.evaluations if eval.is_aggregator
                ],
                parse=req.parse,
                is_dev=req.is_dev_request,
                format_to_issues_scores=req.format_to_issues_scores,
            )
            publish_messages(stage1_messages)
            logger.debug(f"Re-published messages for run_id {run.id}")

            return RunStatusResponse(
                run_id=run.id,
                status=run.status,
                stage1_left=run.stage1_left,
                stage2_left=run.stage2_left,
                stage1_failed=run.stage1_failed,
                stage2_failed=run.stage2_failed,
                created_at=str(datetime.now()),
                updated_at=str(datetime.now()),
            )
    except Exception as e:
        logger.error(f"Error in re-publishing messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(traceback.format_exc()))


# Endpoint to initiate a run and create evaluations
@router.post("/with-evaluator/{evaluator_name}/", response_model=BatchRunStatusResponse)
@router.post("/with-evaluator/{evaluator_name}", response_model=BatchRunStatusResponse)
def initiate_run_with_evaluator(
    evaluator_name: str,
    req: BatchRunRequestNoEvaluator,
    user: models.User = Depends(get_current_user),
):
    """Initiate a run with multiple evaluations for a single input but for all evaluations in the first stage aka "evaluations" use provided in url evaluator instead of the one in configs."""
    all_runs = []
    try:
        with get_db_ctx() as db:
            evaluator = (
                db.query(models.Evaluator)
                .filter(models.Evaluator.name == evaluator_name)
                .first()
            )
        if evaluator is None:
            logger.error(f"Evaluator with name {evaluator_name} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Evaluator with name {evaluator_name} not found",
            )

        # Replace evaluations in req with EvaluationRequest instances
        updated_evaluations = []
        for eval_no_evaluator in req.evaluations:
            updated_evaluations.append(
                EvaluationRequest.from_no_evaluator(eval_no_evaluator, evaluator.id)
            )

        req.evaluations = updated_evaluations
        all_runs_dict = create_run_and_evaluations(req)
        logger.debug(
            f"Created run and evaluations with evaluator {evaluator_name} successfully"
        )
    except Exception as e:
        logger.error(f"Error in creating run and evaluations with evaluator: {str(e)}")
        raise HTTPException(status_code=500, detail=str(traceback.format_exc()))

    try:
        for run_item in all_runs_dict["runs"]:
            stage1_messages = create_stage_pubsub_messages(
                evaluation_ids=run_item["stage1_eval_ids"],
                input_data=run_item["input"],
                input_type=run_item["input_type"],
                stage2_eval_ids=run_item["stage2_eval_ids"],
                parse=req.parse,
                format_to_issues_scores=req.format_to_issues_scores,
            )
            publish_messages(stage1_messages)
            logger.debug(f"Published messages for run_id {run_item['run_id']}")
            all_runs.append(
                {"run_id": run_item["run"].id, "status": run_item["run"].status}
            )
        logger.debug("Completed processing all runs with evaluator")
    except Exception as e:
        logger.error(f"Error in processing runs with evaluator: {str(e)}")
        raise HTTPException(status_code=500, detail=str(traceback.format_exc()))

    return BatchRunStatusResponse(
        batch_run_id=all_runs_dict["batch_run"].id,
        created_at=all_runs_dict["batch_run"].created_at,
        updated_at=all_runs_dict["batch_run"].updated_at,
        engagement_name=req.engagement_name,
        project_name=req.project_name,
        runs=all_runs,
        is_batch_ready=False,
        runs_left=len(all_runs),
    )


@router.get("/{run_id}/status/", response_model=RunStatusResponse)
@router.get("/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(
    run_id: int,
    user: models.User = Depends(get_current_user),
    db=Depends(database.get_db_gen),
):
    """Get a small status object to see if the evaluations are complete.

    Possible values are:

         # Status Descriptions:

         - "pending" - Not started yet.
         - "in_progress" - Started processing.
         - "success" - All evaluations successfully completed.
         - "failed" - Critical failure or all evaluations failed.
         - "partial_fail" - Some evaluations failed. See failed counters for evaluations and aggregated evaluations.
    """
    db_run = db.query(models.Run).filter(models.Run.id == run_id).first()
    if db_run is None:
        logger.error(f"Run with ID {run_id} not found")
        raise HTTPException(status_code=404, detail="Run not found")

    logger.debug(f"Retrieved status for run_id {run_id}")
    return RunStatusResponse(
        created_at=db_run.created_at,
        updated_at=db_run.updated_at,
        engagement_id=db_run.user_project_role.project.engagement_id,
        project_name=db_run.user_project_role.project.name,
        run_id=db_run.id,
        status=db_run.status,
    )


@router.get("/batch/{batch_run_id}/status/", response_model=BatchRunStatusResponse)
@router.get("/batch/{batch_run_id}/status", response_model=BatchRunStatusResponse)
def batch_status(
    batch_run_id: int,
    db: Session = Depends(database.get_db_gen),
    user: models.User = Depends(get_current_user),
):
    """Initiate a run with multiple evaluations for a single input."""
    batch_run = (
        db.query(models.BatchRun).filter(models.BatchRun.id == batch_run_id).first()
    )
    if batch_run is None:
        logger.error(f"Batch run with ID {batch_run_id} not found")
        raise HTTPException(status_code=404, detail="Batch run not found")

    runs = db.query(models.Run).filter(models.Run.batch_run_id == batch_run_id).all()
    run_statuses = [{"run_id": run.id, "status": run.status} for run in runs]
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


@router.get("/batch/{batch_run_id}", response_model=BatchRunResponse)
@router.get("/batch/{batch_run_id}/", response_model=BatchRunResponse)
def get_batch_run(
    batch_run_id: int,
    db: Session = Depends(database.get_db_gen),
    user: models.User = Depends(get_current_user),
):
    """Retrieve details for a specific batch run."""
    batch_run = (
        db.query(models.BatchRun).filter(models.BatchRun.id == batch_run_id).first()
    )
    if batch_run is None:
        logger.error(f"Batch run with ID {batch_run_id} not found")
        raise HTTPException(status_code=404, detail="Batch run not found")

    runs = db.query(models.Run).filter(models.Run.batch_run_id == batch_run_id).all()
    run_responses = []
    for run in runs:
        run_responses.append(get_run_response(run))

    return BatchRunResponse(
        batch_run_id=batch_run.id,
        created_at=batch_run.created_at,
        updated_at=batch_run.updated_at,
        runs=run_responses,
    )


def get_run_response(run_orm):
    all_evaluations = {"stage1": [], "stage2": []}
    for evaluation in run_orm.evaluations:
        evaluation_resp = EvaluationResponse(
            evaluator_id=evaluation.evaluator_id,
            name=evaluation.name,
            status=evaluation.status,
            fail_reason=evaluation.fail_reason,
            output=evaluation.output,
            is_used_for_aggregation=evaluation.is_used_for_aggregation,
        )
        if evaluation.is_aggregator:
            all_evaluations["stage2"].append(evaluation_resp)
        else:
            all_evaluations["stage1"].append(evaluation_resp)

    return RunResponse(
        created_at=run_orm.created_at,
        updated_at=run_orm.updated_at,
        evaluations_failed=run_orm.stage1_failed,
        aggregated_evaluations_failed=run_orm.stage2_failed,
        engagement_id=run_orm.user_project_role.project.engagement_id,
        project_name=run_orm.user_project_role.project.name,
        run_id=run_orm.id,
        status=run_orm.status,
        item_metadata=run_orm.item_metadata,
        evaluations=all_evaluations["stage1"],
        aggregated_evaluations=all_evaluations["stage2"],
    )


@router.get("/{run_id}", response_model=RunResponse)
@router.get("/{run_id}/", response_model=RunResponse)
def get_run(
    run_id: int,
    db=Depends(database.get_db_gen),
    user: models.User = Depends(get_current_user),
):
    """
    Retrieve full run details including item metadata, evaluation results, and aggregated evaluation results in addition to the run status object.
    """
    db_run = db.query(models.Run).filter(models.Run.id == run_id).first()
    if db_run is None:
        logger.error(f"Run with ID {run_id} not found")
        raise HTTPException(status_code=404, detail="Run not found")
    return get_run_response(db_run)
