import os
import signal
import threading
import time
import timeit
import traceback
import cProfile
import pstats
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed

import redis
from google.cloud import pubsub_v1
from google.oauth2 import service_account

from app.db_api.database import get_db_ctx
from app.db_api.models import Evaluation, Run

# Configure logging
from app.logging_config import (
    clear_log_context,
    set_log_context,
    worker_logger as logger,
)
from common.constants import GOOGLE_API_CREDENTIALS_PATH
from common.pubsub_queue import EvaluationStatus, RunStatus
from common.utils import load_env
from evaluators.library import (
    CBCTwoStageEvaluator,
    EchoSingleStageMessagesEvaluator,
    RLHFEvaluator,
    SingleStageMessagesEvaluator,
    SingleStageSystemPromptAspectorEvaluator,
    SingleStageSystemPromptCellwiseAspectorEvaluator,
    SingleStageSystemPromptEvaluator,
    SpecificSingleStageSystemPromptAspectorEvaluator,
    ExecutionCompatabilityEvaluator,
    EvaluationPlagiarismChecker,
    EvaluationAIChecker
)
from workers.utils import deserialize_message, get_input_data_for_review

# Load environment variables
env_vars = load_env()
PROJECT_ID = env_vars["GOOGLE_CLOUD_PROJECT"]
SUBSCRIPTION_ID = env_vars["PUBSUB_TOPIC_SUB"]
global_processed_messages = []

# Initialize Pub/Sub subscriber client with credentials
credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_API_CREDENTIALS_PATH
)
subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
redis_host = env_vars.get("REDIS_HOST", "localhost")
redis_port = int(env_vars.get("REDIS_PORT", 6379))
redis_db = int(env_vars.get("REDIS_DB", 0))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)

max_workers = int(env_vars.get("MAX_WORKERS", 10))
executor = ThreadPoolExecutor(max_workers=max_workers)

profiling_enabled = env_vars.get("ENABLE_PROFILING", "0") == "1"
debug_mode = env_vars.get("DEBUG", "0") == "1"

EVALUATOR_TYPES_MAP = {
    "single_stage_system_prompt": SingleStageSystemPromptEvaluator,
    "single_stage_system_prompt_aspector": SingleStageSystemPromptAspectorEvaluator,
    "single_stage_system_prompt_cellwise_aspector": SingleStageSystemPromptCellwiseAspectorEvaluator,
    "RLHFEvaluator": RLHFEvaluator,
    "specific_quality_aspector_single_stage": SpecificSingleStageSystemPromptAspectorEvaluator,
    "single_stage_messages_evaluator": SingleStageMessagesEvaluator,
    "cbc_two_stage_evaluator": CBCTwoStageEvaluator,
    "EchoSingleStageMessagesEvaluator": EchoSingleStageMessagesEvaluator,
    "notebook_code_compatibility_evaluator":ExecutionCompatabilityEvaluator,
    "plagiarism_checker": EvaluationPlagiarismChecker,
    "ai_generated_checker":EvaluationAIChecker
}


def ack(subscription_path, subscriber, message):
    logger.info(f"Acknowledging message with ID: {message.message.message_id}")
    subscriber.acknowledge(subscription=subscription_path, ack_ids=[message.ack_id])


def fail_run(run_id, error_message):
    with get_db_ctx() as session:
        evaluations_to_fail = (
            session.query(Evaluation)
            .filter(
                Evaluation.run_id == run_id,
                Evaluation.status.in_(
                    [EvaluationStatus.PENDING.value, EvaluationStatus.QUEUED.value]
                ),
            )
            .with_for_update()
            .all()
        )

        failed_count_aggregator_true = 0
        failed_count_aggregator_false = 0

        for eval_to_process in evaluations_to_fail:
            eval_to_process.status = EvaluationStatus.FAILED.value
            sep = "\n\n.......\n\n"
            eval_to_process.fail_reason = (
                error_message[: 500 - len(sep)] + sep + error_message[-500:]
            )
            if eval_to_process.is_aggregator:
                failed_count_aggregator_true += 1
            else:
                failed_count_aggregator_false += 1
    with get_db_ctx() as session:
        run_to_update = (
            session.query(Run).filter(Run.id == run_id).with_for_update().one()
        )
        run_to_update.status = RunStatus.FAILED.value
        run_to_update.stage2_failed += failed_count_aggregator_true
        run_to_update.stage2_left -= failed_count_aggregator_true
        run_to_update.stage1_failed += failed_count_aggregator_false
        run_to_update.stage1_left -= failed_count_aggregator_false
        logger.info(
            "Failed evaluations and run updated due to stage 2 message failure."
        )


def get_run_id_from_evaluation_id(evaluation_id):
    with get_db_ctx() as session:
        evaluation = (
            session.query(Evaluation)
            .filter(Evaluation.id == evaluation_id)
            .with_for_update()
            .one()
        )
        return evaluation.run_id


def update_run_table(run_id, **kwargs):
    try:
        logger.info(
            f"Updating run table for run_id: {run_id} with the following parameters: {kwargs}"
        )
        with get_db_ctx() as session:
            run = session.query(Run).filter(Run.id == run_id).with_for_update().one()
            for key, value in kwargs.items():
                if hasattr(run, key):
                    setattr(run, key, value)
                    if debug_mode:
                        logger.debug(f"Key={key}, Value={value} updated in Run")
            # session.commit()
            logger.info(f"Run {run_id} updated. Current status: {run.status}")
    except Exception as e:
        logger.error(
            f"Failed to update run status for run_id: {run_id} with parameters: {kwargs} due to error: {str(e)}"
        )


def update_evaluation_status(
    evaluation_id, status, evaluation_result, fail_reason: str | None = None
):
    with get_db_ctx() as session:
        evaluation = (
            session.query(Evaluation)
            .filter(Evaluation.id == evaluation_id)
            .with_for_update()
            .one()
        )
        evaluation.status = status
        evaluation.output = evaluation_result
        if fail_reason is not None:
            sep = "\n\n.......\n\n"
            evaluation.fail_reason = (
                fail_reason[: 500 - len(sep)] + sep + fail_reason[-500:]
            )
        # session.commit()


def parse_and_update_run_status(
    stage1_results, stage2_results, stage1_ids, stage2_ids, run_id
):
    # Stage 1 result findings and processings
    stage1_success_count = len(
        [
            result
            for result in stage1_results.values()
            if result["status"] == EvaluationStatus.SUCCESS
        ]
    )

    # Stage 2 result finding and analysis
    stage2_success_count = len(
        [
            result
            for result in stage2_results.values()
            if result["status"] == EvaluationStatus.SUCCESS
        ]
    )

    stage2_left = len(
        [
            result
            for result in stage2_results.values()
            if result["status"]
            in [
                EvaluationStatus.PENDING,
                EvaluationStatus.QUEUED,
                EvaluationStatus.IN_PROGRESS,
            ]
        ]
    )
    if stage2_left != 0:
        logger.critical(
            f"Stage 2 evaluations incomplete. {stage2_left} evaluations left."
        )
        raise Exception(
            f"Stage 2 evaluations incomplete. {stage2_left} evaluations left."
        )

    stage2_failed = len(
        [
            result
            for result in stage2_results.values()
            if result["status"] == EvaluationStatus.FAILED
        ]
    )

    # Update run table
    if stage1_success_count == len(stage1_ids) and (
        stage2_ids is None or stage2_success_count == len(stage2_ids)
    ):
        update_run_table(
            run_id,
            status=RunStatus.SUCCESS.value,
            stage2_left=0,
            stage2_failed=stage2_failed,
        )
    elif stage1_success_count > 0 or stage2_success_count > 0:
        update_run_table(
            run_id,
            status=RunStatus.PARTIAL_FAIL.value,
            stage2_left=0,
            stage2_failed=stage2_failed,
        )
    else:
        update_run_table(
            run_id,
            status=RunStatus.FAILED.value,
            stage2_left=0,
            stage2_failed=stage2_failed,
        )


def prepare_evaluation(evaluation_id, is_dev_req):
    start_time = timeit.default_timer()
    evaluator_config_dict = {
        "name": None,
        "config": None,
        "llm_config": {
            "provider": None,
            "model": None,
            "params": None,
        },
        "config_schema": None,
        "input_schema": None,
        "output_schema": None,
    }
    logger.info(f"Preparing evaluation for id: {evaluation_id}")
    with get_db_ctx() as session:
        evaluation = (
            session.query(Evaluation)
            .filter(Evaluation.id == evaluation_id)
            .with_for_update()
            .first()
        )
        if evaluation is None:
            raise ValueError(
                f"Evaluation with id {evaluation_id} not found in the database."
            )
        if evaluation.status not in (
            EvaluationStatus.QUEUED.value,
            EvaluationStatus.PENDING.value,
        ):
            logger.error(
                f"Evaluation status for id {evaluation_id} is not queued. Got: {evaluation.status}"
            )
            return None
        evaluation.status = EvaluationStatus.IN_PROGRESS.value
        run_id = evaluation.run_id
        eval_config = evaluation.config
        evaluator_type_name = None
        if evaluation.evaluator_id is not None:
            evaluator_orm = evaluation.evaluator
            evaluator_type_orm = evaluator_orm.evaluator_type
            evaluator_type_name = evaluator_type_orm.name

            evaluator_config_dict = {
                "name": evaluator_orm.name,
                "config": evaluator_orm.config,
                "llm_config": {
                    "provider": evaluator_orm.llm_provider,
                    "model": evaluator_orm.llm_model,
                    "params": evaluator_orm.llm_params,
                },
                "config_schema": evaluator_type_orm.config_schema,
                "input_schema": evaluator_orm.input_schema,
                "output_schema": evaluator_orm.output_schema,
            }
        elif is_dev_req:
            evaluator_config_override = evaluation.evaluator_config_override
            if evaluator_config_override.get("evaluator_type_name", None):
                evaluator_type_name = evaluator_config_override["evaluator_type_name"]
            for key in evaluator_config_dict:
                if evaluator_config_override.get(key, None):
                    evaluator_config_dict[key] = evaluator_config_override[key]
            evaluator_config_dict["config_validation"] = False
            logger.info("Dev req %s", evaluator_config_dict)
        else:
            logger.error(
                f"No evaluator configuration found for evaluation id {evaluation_id} and not a dev request."
            )
            raise ValueError("No evaluator configuration found and not a dev request.")

    with get_db_ctx() as session:
        run = session.query(Run).filter(Run.id == run_id).with_for_update().one()
        if run.status == RunStatus.PENDING.value:
            run.status = RunStatus.IN_PROGRESS.value
        elif run.status != RunStatus.IN_PROGRESS.value:
            raise Exception("Invalid run status for evaluation progression.")

    EvaluatorClass = EVALUATOR_TYPES_MAP[evaluator_type_name]
    logger.info(f"Evaluator class {EvaluatorClass.__name__} prepared.")
    duration = timeit.default_timer() - start_time
    logger.info(
        f"Preparation of evaluation id {evaluation_id} completed in {duration:.2f} seconds."
    )
    return (EvaluatorClass(**evaluator_config_dict), eval_config, run_id)


# Define a function to run evaluation for a single message and a single evaluator
def run_single_evaluation(
    single_conversation, evaluation_id, is_dev_req, parse, format_to_issues_scores
):
    set_log_context(thread_name=threading.current_thread().name)
    run_id = None
    start_time = timeit.default_timer()
    try:
        evaluator_out = prepare_evaluation(evaluation_id, is_dev_req)
        if evaluator_out is None:
            return None
        evaluator, eval_config, run_id = evaluator_out
        start_eval_time = timeit.default_timer()
        evaluation_result = evaluator.evaluate(
            single_conversation,
            eval_config,
            input_validation=not is_dev_req,
            parse=parse,
            format_to_issues_scores=format_to_issues_scores,
        )
        eval_time_elapsed = timeit.default_timer() - start_eval_time
        logger.info(f"Evaluation time: {eval_time_elapsed:.2f} seconds.")

        elapsed_time = timeit.default_timer() - start_time
        logger.info(
            f"Evaluation id {evaluation_id} completed successfully in {elapsed_time:.2f} seconds."
        )
        return {
            "run_id": run_id,
            "evaluation_id": evaluation_id,
            "result": evaluation_result,
            "status": EvaluationStatus.SUCCESS,
        }

    except Exception as e:
        elapsed_time = timeit.default_timer() - start_time
        logger.exception(
            f"Evaluation id {evaluation_id} failed after {elapsed_time:.2f} seconds."
        )
        return {
            "run_id": run_id,
            "evaluation_id": evaluation_id,
            "result": None,
            "fail_reason": traceback.format_exc().strip(),
            "status": EvaluationStatus.FAILED,
        }


def process_message(pubsub_message, pubsub_message_id):
    """
    pubsub_message is a list that contains three elements:
    - stage1ids: A list of IDs for the first stage of processing.
    - stage2ids: A list of IDs for the second stage of processing.
    - messages: A list of messages to be processed.
    """

    input_data = pubsub_message.input
    input_type = pubsub_message.input_type
    stage1_ids = pubsub_message.stage1_ids
    stage2_ids = pubsub_message.stage2_ids
    is_dev_req = pubsub_message.is_dev
    aux_params = pubsub_message.aux_params
    parse = (
        pubsub_message.aux_params.get("parse") if pubsub_message.aux_params else None
    )
    format_to_issues_scores = (
        pubsub_message.aux_params.get("format_to_issues_scores")
        if pubsub_message.aux_params
        else None
    )

    def handle_message(raw_conversation):

        set_log_context(
            message_id=pubsub_message_id, thread_name=threading.current_thread().name
        )
        logger.info(f"Processing conversation: {raw_conversation}")
        input_conversation = get_input_data_for_review(input_type, raw_conversation)

        def run_stage_evaluations(stage_ids, input_data, stage_number):
            start_time = timeit.default_timer()
            logger.info(f"Starting stage {stage_number} evaluations.{stage_ids}")
            futures = {
                executor.submit(
                    run_single_evaluation,
                    input_data,
                    stage_id,
                    is_dev_req,
                    parse,
                    format_to_issues_scores and stage_number == 1,
                ): stage_id
                for stage_id in stage_ids
            }
            all_results = {}
            for future in as_completed(futures):
                stage_id = futures[future]
                try:
                    result = future.result()

                    if result is None:
                        logger.warning(
                            f"Stage {stage_number} evaluation for id: {stage_id} returned None."
                        )
                        continue

                    all_results[stage_id] = result
                    if result["status"] == EvaluationStatus.SUCCESS:
                        logger.info(
                            f"Stage {stage_number} evaluation for id: {stage_id} completed successfully."
                        )
                    else:
                        logger.warning(
                            f"Stage {stage_number} evaluation for id: {stage_id} did not succeed. Status: {result['status']}"
                        )
                except Exception as e:
                    logger.exception(
                        f"Stage {stage_number} evaluation failed for id: {stage_id}",
                        exc_info=e,
                    )
                    all_results[stage_id] = {
                        "evaluation_id": stage_id,
                        "fail_reason": traceback.format_exc(),
                        "status": EvaluationStatus.FAILED,
                    }

            for stage_id, result in all_results.items():
                fail_reason = result.get("fail_reason", None)
                if fail_reason:
                    update_evaluation_status(
                        stage_id, result["status"].value, None, fail_reason
                    )
                else:
                    update_evaluation_status(
                        stage_id, result["status"].value, result["result"]
                    )
                logger.info(
                    f"Updated status for stage {stage_number} evaluation id: {stage_id} to {result['status']}."
                )

            elapsed = timeit.default_timer() - start_time
            logger.info(
                f"Completed stage {stage_number} evaluations in {elapsed:.2f} seconds."
            )
            return all_results

        try:
            # Run stage 1 evaluations concurrently
            if debug_mode:
                logger.debug(f"Input conversation: {input_conversation}")
                logger.debug(f"Stage 1 IDs: {stage1_ids}")

            stage1_results = run_stage_evaluations(stage1_ids, input_conversation, 1)

            stage1_start_time = timeit.default_timer()
            if not stage1_results:
                update_run_table(
                    get_run_id_from_evaluation_id(stage1_ids[0]),
                    status=RunStatus.SUCCESS.value,
                )
                logger.info("Stage 1 evaluations completed with no results to process.")
                return

            stage1_left = len(
                [
                    result
                    for stage1_id, result in stage1_results.items()
                    if result["status"]
                    in [
                        EvaluationStatus.PENDING,
                        EvaluationStatus.QUEUED,
                        EvaluationStatus.IN_PROGRESS,
                    ]
                ]
            )
            if stage1_left != 0:
                logger.critical(
                    f"Stage 1 evaluations incomplete. {stage1_left} evaluations left."
                )
                raise Exception(
                    f"Stage 1 evaluations incomplete. {stage1_left} evaluations left."
                )

            stage1_failed = [
                result
                for stage1_id, result in stage1_results.items()
                if result["status"] == EvaluationStatus.FAILED
            ]
            total_stage1_failed = len(stage1_failed)

            if stage2_ids:
                status = RunStatus.IN_PROGRESS.value
            elif total_stage1_failed == 0:
                status = RunStatus.SUCCESS.value
            elif total_stage1_failed == len(stage1_ids):
                status = RunStatus.FAILED.value
            elif total_stage1_failed > 0:
                status = RunStatus.PARTIAL_FAIL.value
            else:
                logger.critical("We are in a weird no status state.")
                raise Exception("We are in a weird no status state.")

            run_id = next(iter(stage1_results.values()), {})["run_id"]
            update_run_table(
                run_id,
                status=status,
                stage1_left=0,
                stage1_failed=total_stage1_failed,
            )
            stage1_elapsed = timeit.default_timer() - stage1_start_time
            logger.info(
                f"Stage 1 evaluations completed in {stage1_elapsed:.2f} seconds. Status: {status}, Stage 1 failed: {total_stage1_failed}"
            )

            # Run stage 2 evaluations concurrently
            stage2_start_time = (
                timeit.default_timer()
            )  # Start timing for stage 2 evaluations

            stage2_input_data = {
                "original_input": input_conversation,
                "evaluations": [
                    result["result"]
                    for result in stage1_results.values()
                    if result["status"] == EvaluationStatus.SUCCESS
                ],
            }

            if stage2_ids is not None:
                stage2_results = run_stage_evaluations(stage2_ids, stage2_input_data, 2)
            else:
                stage2_results = {}

            parse_and_update_run_status(
                stage1_results, stage2_results, stage1_ids, stage2_ids, run_id
            )

            stage2_elapsed = (
                timeit.default_timer() - stage2_start_time
            )  # End timing for stage 2 evaluations
            logger.info(
                f"Stage 2 evaluations completed in {stage2_elapsed:.2f} seconds. "
                "Stage 1 and Stage 2 evaluations have been processed."
            )

        except Exception as e:
            logger.exception("Failed to prepare or publish stage 2 messages.")
            fail_run(
                pubsub_message,
                "Failed to prepare or publish aggregation stage evaluations.",
            )

    logger.info(f"Pubsub message input: {pubsub_message.input}")
    logger.info(f"Length of pubsub message input: {len(pubsub_message.input)}")

    start_time = timeit.default_timer()
    handle_message_count = 0

    if isinstance(pubsub_message.input, list):
        responses = [
            executor.submit(handle_message, input_item)
            for input_item in pubsub_message.input
        ]
        handle_message_count += len(responses)
        for future in as_completed(responses):
            try:
                res = future.result()  # or collect results if needed
                if debug_mode:
                    logger.debug(f"Result: {res}")
                logger.info("Bye")
            except Exception as e:
                logger.exception(
                    f"An error occurred while processing the message: {e}. Traceback: {traceback.format_exc()}"
                )
    else:
        responses = handle_message(pubsub_message.input)
        handle_message_count += 1
        if debug_mode:
            logger.debug(f"~~~Result: {responses}")

    elapsed = timeit.default_timer() - start_time
    logger.info(
        f"Time taken to process and get response: {elapsed} seconds. handle_message was called {handle_message_count} times in this duration."
    )


def process_and_acknowledge(message):
    start_time = timeit.default_timer()
    message_id = message.message.message_id

    set_log_context(message_id=message_id, thread_name=threading.current_thread().name)

    try:
        # Check if message_id is already processed or being processed
        if redis_client.get(message_id):
            logger.info("Message already processed or being processed, skipping...")
            ack(subscription_path, subscriber, message)
            return

        # Mark message as being processed
        redis_client.set(message_id, "processing", ex=3600)
        logger.info("Message status set to processing in Redis.")

        # Process the message
        logger.info("Processing and acknowledging the message.")
        pubsub_message = deserialize_message(message.message.data)
        process_message(pubsub_message, message_id)

        # Mark message as processed
        redis_client.set(message_id, "processed", ex=3600)
        logger.info("Message status set to processed in Redis.")

    except redis.exceptions.ConnectionError as redis_error:
        logger.exception("Redis connection error occurred: %s", redis_error)
        # Optionally, you can choose to reprocess the message or exit based on your requirement
    except Exception as e:
        logger.exception(
            f"An error occurred while processing the message: {e}. Traceback: {traceback.format_exc()}"
        )
    finally:
        elapsed = timeit.default_timer() - start_time
        logger.info(
            f"Time taken to process and acknowledge the message: {elapsed:.2f} seconds"
        )
        ack(subscription_path, subscriber, message)
        clear_log_context()


def main():
    # Define a clean exit handler
    def exit_gracefully(signum, frame):
        print("Shutting down gracefully...")
        subscriber.close()
        exit(0)

    # Attach signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    print(f"Listening for messages on {subscription_path}...")

    with subscriber:
        while True:
            response = subscriber.pull(
                subscription=subscription_path, max_messages=1, return_immediately=False
            )
            received_messages = response.received_messages
            if received_messages:
                message = received_messages[0]
                try:
                    process_and_acknowledge(message)
                except Exception as e:
                    logger.exception(
                        f"An error occurred while processing the message: {e}. Traceback: {traceback.format_exc()}"
                    )
                finally:
                    ack(subscription_path, subscriber, message)
                logger.info("Acknowledged message.")
            else:
                # logger.info("No messages received, sleeping for 1 second.")
                time.sleep(1)  # Sleep for a short period before checking again


if __name__ == "__main__":
    main()
