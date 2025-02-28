import logging
import time
import traceback
from enum import Enum

from celery import chain, chord, group, shared_task
from celery.signals import task_failure, worker_process_init
from sqlalchemy import TextClause

from app.db_api.database import get_db_ctx_manual
from app.db_api.models import models
from evaluators.library import (
    CBCTwoStageEvaluator,
    EchoSingleStageMessagesEvaluator,
    RLHFEvaluator,
    SingleStageMessagesEvaluator,
    SingleStageSystemPromptAspectorEvaluator,
    SingleStageSystemPromptCellwiseAspectorEvaluator,
    SingleStageSystemPromptEvaluator,
    SpecificSingleStageSystemPromptAspectorEvaluator,
)
from workers.task_utils import create_evaluations, pull_evaluators_setups


class RunStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_FAIL = "partial_fail"


class EvaluationStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logger = logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

from sqlalchemy import event
from sqlalchemy.engine import Engine


# Function to log query explanations
def explain_query(conn, cursor, statement, parameters, context, executemany):
    if statement.strip().upper().startswith("SELECT"):
        cursor.execute(f"EXPLAIN {statement}", parameters)
        explanation = cursor.fetchall()
        logging.info("Query Explanation: %s", explanation)


# Attach the event listener to the engine
event.listen(Engine, "before_cursor_execute", explain_query)


def save_results(results, run, compiled_evaluations):
    start_time = time.time()
    print(f"Start time: {start_time}")

    def print_args_with_names(**kwargs):
        for name, value in kwargs.items():
            print(f"{name}: {value}")
            print("-----")

    print_args_with_names(
        run=run, compiled_evaluations=compiled_evaluations, results=results
    )
    print("ARE WE REALLY INSIDE SAVE RESULTS FINALLY?")
    mapped_results = {}
    results_list = results["stage1_results"] + results.get("stage2_results", [])
    compiled_evaluations_list = compiled_evaluations[
        "stage1"
    ] + compiled_evaluations.get("stage2", [])
    for r in results_list:
        mapped_results[r["name"]] = r
    print("AAAAAAAAAAAAAAAAAAAAAAA RESULTS")
    print(mapped_results)
    print(compiled_evaluations_list)
    for compiled_eval in compiled_evaluations_list:
        compiled_eval["result"] = mapped_results[compiled_eval["name"]]

    # Time before entering the database context
    before_db_ctx_time = time.time()
    print(
        f"Time before entering DB context: {before_db_ctx_time} (Total elapsed: {before_db_ctx_time - start_time:.2f} seconds, Step elapsed: {before_db_ctx_time - start_time:.2f} seconds)"
    )

    # Time inside the with statement before try block
    inside_with_time = time.time()
    print(
        f"Time inside with statement before try: {inside_with_time} (Total elapsed: {inside_with_time - start_time:.2f} seconds, Step elapsed: {inside_with_time - before_db_ctx_time:.2f} seconds)"
    )

    evaluations = create_evaluations(
        compiled_evaluations=compiled_evaluations_list,
        new_run_id=run["run_id"],
        batch_run_id=run["batch_run_id"],
        user_proj_role_id=run["user_project_obj_id"],
        is_dev_request=run["is_dev_request"],
    )

    # Time after creating evaluations
    after_create_evaluations_time = time.time()
    print(
        f"Time after creating evaluations: {after_create_evaluations_time} (Total elapsed: {after_create_evaluations_time - start_time:.2f} seconds, Step elapsed: {after_create_evaluations_time - inside_with_time:.2f} seconds)"
    )

    # Time after preparing bulk insert mappings
    after_prepare_bulk_insert_mappings_time = time.time()
    print(
        f"Time after preparing bulk insert mappings: {after_prepare_bulk_insert_mappings_time} (Total elapsed: {after_prepare_bulk_insert_mappings_time - start_time:.2f} seconds, Step elapsed: {after_prepare_bulk_insert_mappings_time - after_create_evaluations_time:.2f} seconds)"
    )
    with get_db_ctx_manual() as db:
        try:
            # Bulk insert evaluations
            db.bulk_insert_mappings(models.Evaluation, evaluations["new_evaluations"])
            # Time after bulk insert mappings
            after_bulk_insert_mappings_time = time.time()
            print(
                f"Time after bulk insert mappings: {after_bulk_insert_mappings_time} (Total elapsed: {after_bulk_insert_mappings_time - start_time:.2f} seconds, Step elapsed: {after_bulk_insert_mappings_time - after_prepare_bulk_insert_mappings_time:.2f} seconds)"
            )

            run_to_update = (
                db.query(models.Run)
                .filter(models.Run.id == run["run_id"])
                .with_for_update()
                .one()
            )

            # Time after getting run but before commit
            after_get_run_before_commit_time = time.time()
            print(
                f"Time after getting run but before commit: {after_get_run_before_commit_time} (Total elapsed: {after_get_run_before_commit_time - start_time:.2f} seconds, Step elapsed: {after_get_run_before_commit_time - after_create_evaluations_time:.2f} seconds)"
            )

            if evaluations["success_count"] == 0:
                run_to_update.status = RunStatus.FAILED.value
            elif evaluations["failed_count"] != 0:
                run_to_update.status = RunStatus.PARTIAL_FAIL.value
            else:
                run_to_update.status = RunStatus.SUCCESS.value

            run_to_update.stage2_failed = evaluations["failed_count_stage2"]
            run_to_update.stage2_left = 0
            run_to_update.stage1_failed = evaluations["failed_count_stage1"]
            run_to_update.stage1_left = 0

            db.commit()

            # Time after commit
            after_commit_time = time.time()
            print(
                f"Time after commit: {after_commit_time} (Total elapsed: {after_commit_time - start_time:.2f} seconds, Step elapsed: {after_commit_time - after_get_run_before_commit_time:.2f} seconds)"
            )

        except Exception as e:
            db.rollback()
            traceback.print_exc()
            print(f"Error creating evaluations: {e}")
            raise e

    end_time = time.time()
    print(
        f"End time: {end_time} (Total elapsed: {end_time - start_time:.2f} seconds, Step elapsed: {end_time - after_commit_time:.2f} seconds)"
    )
    print("=" * 90)


# Dummy payloads for testing
dummy_run = {
    "run_id": 1,
    "batch_run_id": 1,
    "user_project_obj_id": 5,
    "is_dev_request": True,
}

dummy_compiled_evaluations = {
    "stage1": [
        {
            "name": f"eval{i}",
            "result": {},
            "is_aggregator": False,
            "use_for_agg_layer": False,
            "config": {},
            "evaluator_orm": {"id": 1},
            "evaluator_config_override": None,
        }
        for i in range(50)
    ],
    "stage2": [
        {
            "name": "eval55",
            "result": {},
            "is_aggregator": True,
            "use_for_agg_layer": True,
            "config": {},
            "evaluator_orm": {"id": 2},
            "evaluator_config_override": None,
        }
    ],
}

dummy_results = {
    "stage1_results": [
        {"name": f"eval{i}", "result": {"result": "success"}} for i in range(50)
    ],
    "stage2_results": [{"name": "eval55", "result": {"result": "success"}}],
}

# Call the function with dummy payloads
save_results(dummy_results, dummy_run, dummy_compiled_evaluations)
save_results(dummy_results, dummy_run, dummy_compiled_evaluations)
