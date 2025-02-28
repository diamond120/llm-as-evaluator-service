import json
import os
import time
import traceback

import celery.exceptions
from celery import chain, chord, current_task, group, shared_task
from celery.result import AsyncResult
from celery.signals import task_failure, worker_process_init
from google.cloud import pubsub_v1
from google.oauth2 import service_account

from sqlalchemy import TextClause

from app.db_api.database import get_db_ctx_manual
from app.db_api.models import models
from app.logging_config import is_json_logging_enabled, logger
from common.constants import GOOGLE_API_CREDENTIALS_PATH
from common.utils import load_env, get_next_queue
from evaluators.library import (
    AppleCodeTranslationEvaluator,
    AppleLLMReviewerProxy,
    AppleTurnByTurnEvaluator,
    CBCTwoStageEvaluator,
    CodeFormatEvaluator,
    EchoSingleStageMessagesEvaluator,
    ExecutionCompatabilityEvaluator,
    GraphCodeCheckerEvaluator,
    GraphLLMEvaluator,
    LintingEvaluator,
    RLHFEvaluator,
    RLHFGlobalEvaluator,
    SingleStageMessagesEvaluator,
    SingleStageSystemPromptAspectorEvaluator,
    SingleStageSystemPromptCellwiseAspectorEvaluator,
    SingleStageSystemPromptEvaluator,
    SpecificSingleStageSystemPromptAspectorEvaluator,
    UnifiedTextFieldGrammarEvaluator,
    EvaluationPlagiarismChecker,
    EvaluationAIChecker
)
from workers.celery_app import celery_app
from workers.task_utils import (
    EvaluationStatus,
    RunStatus,
    create_evaluations,
    pull_evaluators_setups,
)
from workers.webhook_tasks import process_webhook_data

env_vars = load_env()
MAX_CELERY_TASK_TIMEOUT = int(env_vars.get("MAX_CELERY_TASK_TIMEOUT", 800))
PROJECT_ID = env_vars["GOOGLE_CLOUD_PROJECT"]
PUSH_LOGS_TO_PUBSUB = env_vars.get("PUSH_LOGS_TO_PUBSUB", "f").lower() in (
    "true",
    "1",
    "t",
)
PUSH_TO_WEBHOOK = env_vars.get("PUSH_TO_WEBHOOK", "f").lower() in (
    "true",
    "1",
    "t",
)


EVALUATOR_TYPES_MAP = {
    "single_stage_system_prompt": SingleStageSystemPromptEvaluator,
    "single_stage_system_prompt_aspector": SingleStageSystemPromptAspectorEvaluator,
    "single_stage_system_prompt_cellwise_aspector": SingleStageSystemPromptCellwiseAspectorEvaluator,
    "specific_quality_aspector_single_stage": SpecificSingleStageSystemPromptAspectorEvaluator,
    "single_stage_messages_evaluator": SingleStageMessagesEvaluator,
    "EchoSingleStageMessagesEvaluator": EchoSingleStageMessagesEvaluator,
    "RLHFEvaluator": RLHFEvaluator,
    "cbc_two_stage_evaluator": CBCTwoStageEvaluator,
    "GraphCodeCheckerEvaluator": GraphCodeCheckerEvaluator,
    "GraphLLMEvaluator": GraphLLMEvaluator,
    "apple_tbt_evaluator": AppleTurnByTurnEvaluator,
    "apple_llm_reviewer_proxy": AppleLLMReviewerProxy,
    "rlhf_global_evaluator": RLHFGlobalEvaluator,
    "apple_code_translation_evaluator": AppleCodeTranslationEvaluator,
    "unified_text_field_grammar_evaluator": UnifiedTextFieldGrammarEvaluator,
    "notebook_code_compatibility_evaluator": ExecutionCompatabilityEvaluator,
    "plagiarism_checker": EvaluationPlagiarismChecker,
    "ai_generated_checker":EvaluationAIChecker,
    "simple_linter_evaluator": LintingEvaluator,
    "code_format_evaluator": CodeFormatEvaluator,
}

credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_API_CREDENTIALS_PATH
)
publisher = pubsub_v1.PublisherClient(credentials=credentials)
LOGGING_PUBSUB_TOPIC = os.getenv("LOGGING_PUBSUB_TOPIC", "llm-evaluator-alerts")
topic_path = (
    publisher.topic_path(PROJECT_ID, LOGGING_PUBSUB_TOPIC)
    if LOGGING_PUBSUB_TOPIC
    else None
)


# Initialize OpenTelemetry based on environment variable
# @worker_process_init.connect(weak=False)
# def init_celery_tracing(*args, **kwargs):
#     if os.getenv("ENABLE_OPENTELEMETRY", "False").lower() in ("true", "1", "t"):
#         trace.set_tracer_provider(TracerProvider())
#         span_processor = BatchSpanProcessor(ConsoleSpanExporter())
#         trace.get_tracer_provider().add_span_processor(span_processor)
#         CeleryInstrumentor().instrument()


@worker_process_init.connect
def on_init(*args, **kwargs):
    # relieving cold start
    with get_db_ctx_manual() as sess:
        sess.execute(TextClause("SELECT 1"))


@task_failure.connect
def on_unhandled_non_celery_error(
    task_id, exception, args, kwargs, traceback, einfo, **compat_kwargs
):
    """
    Handle unhandled non-Celery errors.
    """

    def detect_run_id(args, kwargs):
        for arg in args:
            if isinstance(arg, dict) and "run_id" in arg:
                return arg["run_id"]
        for kwarg in kwargs.values():
            if isinstance(kwarg, dict) and "run_id" in kwarg:
                return kwarg["run_id"]
        return None

    run_id = detect_run_id(args, kwargs)
    if run_id is not None:
        fail_run.apply_async(args=[run_id], queue=get_next_queue("process_queue"))

    logger.error(f"Task ID: {task_id}")
    logger.error(f"Exception: {exception}")
    logger.error(f"Args: {args}")
    logger.error(f"Kwargs: {kwargs}")
    logger.error(f"Traceback: {traceback}")
    logger.error(f"Exception Info: {einfo}", exc_info=True)


@celery_app.task
def compile_evaluations(run, evaluations_configs, aggregated_evaluations_configs):
    logger.debug("Entering compile_evaluations task")
    with get_db_ctx_manual() as db:
        try:
            evaluations = pull_evaluators_setups(
                db,
                evaluations_configs,
                aggregated_evaluations_configs,
                is_dev_request=run["is_dev_request"],
                parse=run["parse"],
                format_to_issues_scores=run["format_to_issues_scores"],
            )
            stage1_evaluations = [
                eval for eval in evaluations if not eval["is_aggregator"]
            ]
            stage2_evaluations = [eval for eval in evaluations if eval["is_aggregator"]]
            logger.debug("Leaving compile_evaluations task")
            return {"stage1": stage1_evaluations, "stage2": stage2_evaluations}
        except Exception as e:
            db.rollback()
            logger.error("Failed to compile evaluations.", exc_info=e)
            logger.debug("Leaving compile_evaluations task with error")
            raise e


@celery_app.task(
    rate_limit="8000/m",
    soft_time_limit=MAX_CELERY_TASK_TIMEOUT - 40,
)
def evaluate(input_payload, evaluator_setup, run_id, engagement_name):
    task_id = current_task.request.id if current_task else None
    logger.debug("Entering evaluate task")
    out = {
        "name": None,
        "result": None,
        "use_for_agg_layer": False,
        "run_id": run_id,
        "token_usage": {},
    }
    try:
        out["name"] = evaluator_setup["name"]
        out["use_for_agg_layer"] = evaluator_setup["use_for_agg_layer"]
        evaluator_type_name = evaluator_setup["evaluator_type_orm"]["name"]
        evaluator_class = EVALUATOR_TYPES_MAP[evaluator_type_name]
        evaluator = evaluator_class(
            name=evaluator_setup["name"],
            config=evaluator_setup["evaluator_type_config"],
            llm_config=evaluator_setup["llm_config"],
            config_schema=evaluator_setup["config_schema"],
            input_schema=evaluator_setup["input_schema"],
            output_schema=evaluator_setup["output_schema"],
            run_id=run_id,
            engagement_name=engagement_name,
        )
        try:
            evaluated_result = evaluator.evaluate(
                input_data=input_payload,
                config=evaluator_setup["config"],
                input_validation=True,
                parse=evaluator_setup["parse"],
                format_to_issues_scores=evaluator_setup["format_to_issues_scores"],
            )
            out["result"] = evaluated_result["result"]
            out["token_usage"] = evaluated_result.get("metadata", {})
        except Exception as e:
            if is_json_logging_enabled():
                logger.exception(
                    f"Evaluator evaluate method failed for run_id {run_id}, evaluator name: {evaluator_setup['name']}, evaluator type: {evaluator_setup['evaluator_type_orm']['name']}.",
                    extra={
                        "run_id": run_id,
                        "evaluator_name": evaluator_setup["name"],
                        "evaluator_type": evaluator_setup["evaluator_type_orm"]["name"],
                        "input_payload": input_payload,
                        "evaluator_setup": evaluator_setup,
                        "traceback": traceback.format_exc(),
                    },
                    exc_info=e,
                )
            else:
                logger.error(
                    f"Evaluator evaluate method failed for run_id {run_id}, evaluator name: {evaluator_setup['name']}, evaluator type: {evaluator_setup['evaluator_type_orm']['name']}. {traceback.format_exc()}",
                    exc_info=e,
                )
            raise e
            # logger.error(
            #     f"First attempt to evaluate failed for run_id {run_id}.", exc_info=e
            # )
            # try:
            #     out["result"] = evaluator.evaluate(
            #         input_data=input_payload,
            #         config=evaluator_setup["config"],
            #         input_validation=True,
            #         parse=evaluator_setup["parse"],
            #         format_to_issues_scores=evaluator_setup["format_to_issues_scores"],
            #     )
            # except Exception as e:
            #     logger.error(
            #         f"Second attempt to evaluate failed for run_id {run_id}.",
            #         exc_info=e,
            #     )
            #     raise e
        logger.debug("Leaving evaluate task")
        return out
    except Exception as e:
        if is_json_logging_enabled():
            logger.exception(
                f"EvaluationException: for {evaluator_setup['name']} - {run_id}.",
                extra={
                    "run_id": run_id,
                    "celery_task_id": task_id,
                    "traceback": traceback.format_exc(),
                },
            )
        else:
            logger.error(
                f"EvaluationException: {evaluator_setup['name']} - {run_id}. {traceback.format_exc()}",
                exc_info=True,
            )

        out["fail_reason"] = str(e)
        out["traceback"] = traceback.format_exc()
        logger.debug("Leaving evaluate task with error")

        return out


@celery_app.task
def save_results(prepared_output, task_id=None, run_id=None):
    try:
        if task_id is not None:
            try:
                start_time = time.time()
                async_result = AsyncResult(task_id)
                intermediate_result = async_result.get(
                    timeout=MAX_CELERY_TASK_TIMEOUT - 30, disable_sync_subtasks=False
                )
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Time elapsed for async_result.get: {elapsed_time:.2f} seconds"
                )
            except celery.exceptions.TimeoutError as e:
                logger.error(f"Initial task timed out. Task ID: {task_id}", exc_info=e)
                async_result.revoke(terminate=True)
                fail_run.apply_async(args=[run_id], queue=get_next_queue("process_queue"))
                return

            try:
                start_time = time.time()
                prepared_output = AsyncResult(intermediate_result).get(
                    timeout=MAX_CELERY_TASK_TIMEOUT - 20 - elapsed_time,
                    disable_sync_subtasks=False,
                )
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Time elapsed for prepared output  {elapsed_time:.2f} seconds"
                )
            except celery.exceptions.TimeoutError as e:
                logger.error(
                    f"Intermediate task timed out. Task ID: {task_id} and intermediate: {intermediate_result}",
                    exc_info=e,
                )
                AsyncResult(intermediate_result).revoke(terminate=True)
                fail_run.apply_async(args=[run_id], queue=get_next_queue("process_queue"))
                return
        logger.debug("Entering save_results task")
        run = prepared_output["run"]
        run_fields = prepared_output["run_fields"]
        evaluations = prepared_output["evaluations"]

        start_time = time.time()

        with get_db_ctx_manual() as db:
            try:
                # Bulk insert evaluations
                logger.debug(f"Bulk inserting evaluations: {evaluations}")
                db.bulk_insert_mappings(models.Evaluation, evaluations)
                run_to_update = (
                    db.query(models.Run)
                    .filter(models.Run.id == run["run_id"])
                    .with_for_update()
                    .one()
                )
                for key, value in run_fields.items():
                    setattr(run_to_update, key, value)

                db.commit()
                logger.debug("Leaving save_results task")
            except Exception as e:
                db.rollback()
                logger.error("Failed to save results.", exc_info=e)
                logger.debug("Leaving save_results task with error")
                raise e
        elapsed_time = time.time() - start_time
        logger.info(f"Time elapsed for get_db_ctx_manual {elapsed_time:.2f} seconds")
    except Exception as e:
        logger.error("Failed to save results. Timeout? - ", exc_info=e)
        logger.debug("Leaving save_results task with error")
        fail_run.apply_async(args=[run_id], queue=get_next_queue("process_queue"))
        raise e


@celery_app.task
def fail_run_on_save_error(*args, **kwargs):
    fail_run.apply_async(args=[kwargs["run_id"]], queue=get_next_queue("process_queue"))


@celery_app.task
def fail_run(run_id):
    logger.debug("Entering fail_run task")
    logger.info(f"Fail run initiated with {run_id=}")
    with get_db_ctx_manual() as db:
        try:
            run_to_update = (
                db.query(models.Run)
                .filter(models.Run.id == run_id)
                .with_for_update()
                .one()
            )
            evaluations = (
                db.query(models.Evaluation)
                .filter(models.Evaluation.run_id == run_id)
                .all()
            )
            run_to_update.status = RunStatus.FAILED.value
            stage2_failed_count = sum(
                1
                for e in evaluations
                if e.is_aggregator and e.status == EvaluationStatus.FAILED.value
            )
            stage2_not_success_count = sum(
                1
                for e in evaluations
                if e.is_aggregator and e.status != EvaluationStatus.SUCCESS.value
            )
            stage1_failed_count = sum(
                1
                for e in evaluations
                if not e.is_aggregator and e.status == EvaluationStatus.FAILED.value
            )
            stage1_not_success_count = sum(
                1
                for e in evaluations
                if not e.is_aggregator and e.status != EvaluationStatus.SUCCESS.value
            )
            # since evaluations only created post run, it will prbably all 000s
            run_to_update.stage2_failed = stage2_failed_count
            run_to_update.stage2_left = stage2_not_success_count - stage2_failed_count
            run_to_update.stage1_failed = stage1_failed_count
            run_to_update.stage1_left = stage1_not_success_count - stage1_failed_count
            db.commit()
            logger.info(
                f"Run {run_id} has been marked as failed and the database has been updated."
            )
            logger.debug("Leaving fail_run task")
        except Exception as e:
            db.rollback()
            logger.error("Failed to mark run as failed.", exc_info=e)
            logger.debug("Leaving fail_run task with error")
            raise e


@celery_app.task
def stage2_evaluate(stage1_results, populated_evaluations, run):
    logger.debug("Entering stage2_evaluate task")
    # run is added for error handling signal
    stage2_evaluations = populated_evaluations["stage2"]
    input_evaluations = []
    for r in stage1_results:
        if r["use_for_agg_layer"] and r["result"]:
            if run.get("format_to_issues_scores", False):
                if "issues" in r["result"]:
                    input_evaluations.append(
                        {
                            "issues": [
                                issue
                                for issue in r["result"]["issues"]
                                if len(str(issue)) < 1500
                            ]
                        }
                    )
                else:
                    input_evaluations.append(r["result"])
            else:
                input_evaluations.append(r["result"])

        # Convert each added input evaluation to string and truncate if necessary
        for i, evaluation in enumerate(input_evaluations):
            evaluation_str = str(evaluation)
            if len(evaluation_str) > 10000:
                input_evaluations[i] = (
                    evaluation_str[:10000]
                    + " (cut due to being too long but it's okay)"
                )
            else:
                input_evaluations[i] = evaluation_str

    lazy_chord_evaluations_stage2 = get_evaluations_group(
        {
            "original_input": run["input"],
            "evaluations": input_evaluations,
        },
        stage2_evaluations,
        run["run_id"],
        run["engagement_name"],
    )

    workflow = lazy_chord_evaluations_stage2(
        convert_results_to_dict.s(stage1_results, stage1_results_first=False).set(queue=get_next_queue("evaluation_queue"))
        | prepare_output_for_saving.s(run, populated_evaluations).set(queue=get_next_queue("evaluation_queue"))
    )
    result = workflow.get(disable_sync_subtasks=False)
    logger.debug("Leaving stage2_evaluate task")
    return result


@shared_task
def convert_results_to_dict(
    first_results=None, second_results=None, stage1_results_first=None
):
    logger.debug("Entering convert_results_to_dict task")
    if stage1_results_first is None:
        raise ValueError("stage1_results_first cannot be None")
    # Convert list to dictionary
    if stage1_results_first:
        stage1_results = first_results
        stage2_results = second_results
    else:
        stage2_results = first_results
        stage1_results = second_results
    result = (
        {"stage1_results": stage1_results}
        if stage2_results is None
        else {"stage1_results": stage1_results, "stage2_results": stage2_results}
    )
    logger.debug("Leaving convert_results_to_dict task")
    return result


@shared_task
def evaluate_workflow(populated_evaluations, run, has_aggregated):
    logger.debug("Entering evaluators_workflow task")
    lazy_evaluations_group_stage1 = get_evaluations_group(
        run["input"],
        populated_evaluations["stage1"],
        run["run_id"],
        run["engagement_name"],
    )
    # evaluations_group_stage1: lazy chord
    if has_aggregated:
        async_res_prepared_output = lazy_evaluations_group_stage1(
            stage2_evaluate.s(populated_evaluations, run).set(queue=get_next_queue("evaluation_stage2_queue"))
        )
    else:
        async_res_prepared_output = lazy_evaluations_group_stage1(
            convert_results_to_dict.s(stage1_results_first=True).set(queue=get_next_queue("evaluation_queue"))
            | prepare_output_for_saving.s(run, populated_evaluations).set(queue=get_next_queue("evaluation_queue"))
        )
    logger.debug("Leaving evaluators_workflow task")
    return async_res_prepared_output.task_id


@shared_task
def prepare_output_for_saving(results, run, compiled_evaluations):
    logger.debug("Entering prepare_output_for_saving task")

    mapped_results = {}
    results_list = results["stage1_results"] + results.get("stage2_results", [])
    compiled_evaluations_list = compiled_evaluations[
        "stage1"
    ] + compiled_evaluations.get("stage2", [])
    for r in results_list:
        mapped_results[r["name"]] = r
    for compiled_eval in compiled_evaluations_list:
        compiled_eval["result"] = mapped_results[compiled_eval["name"]]
    evaluations, run_fields, slack_alerts = create_evaluations(
        compiled_evaluations=compiled_evaluations_list,
        new_run_id=run["run_id"],
        batch_run_id=run["batch_run_id"],
        user_proj_role_id=run["user_project_role_id"],
        is_dev_request=run["is_dev_request"],
    )
    logger.debug("Leaving prepare_output_for_saving task")

    # Asynchronously process and send to webhook
    if PUSH_TO_WEBHOOK:
        logger.debug(f"Pushing result to webhook for run_id: {run['run_id']}")
        process_webhook_data.apply_async(
            args=[{"run": run, "evaluations": evaluations}], queue=get_next_queue("webhook_queue")
        )

    # Asynchronously publish exception info to Pub/Sub using a separate logging task if enabled
    if PUSH_LOGS_TO_PUBSUB and slack_alerts:
        logger.debug("Push to logging_queue")
        publish_exception_to_pubsub.apply_async(
            args=[slack_alerts], queue=get_next_queue("logging_queue")
        )

    return {"run": run, "evaluations": evaluations, "run_fields": run_fields}


@celery_app.task
def process_run(run, evaluations, aggregated_evaluations, save_to_db=True):
    logger.debug("Entering process_run task")
    logger.info("Inside process_run function")
    if aggregated_evaluations is None:
        aggregated_evaluations = []
    has_aggregated = bool(aggregated_evaluations)

    populated_evaluations_task = compile_evaluations.s(
        run, evaluations, aggregated_evaluations
    ).set(queue=get_next_queue("db_fetch_queue"))
    # populated_evaluations_task: signature

    workflow_lazy_chain_that_returns_output_task_id = chain(
        populated_evaluations_task,
        evaluate_workflow.s(run, has_aggregated).set(queue=get_next_queue("evaluation_queue")),
    ).apply_async(queue=get_next_queue("evaluation_queue"))
    # workflow_lazy_chain: lazy chain, returns task_id for the final prepared outputs
    logger.info("workflow_lazy_chain ready")
    if save_to_db:
        save_results.apply_async(
            args=[None],
            kwargs={
                "task_id": workflow_lazy_chain_that_returns_output_task_id.task_id,
                "run_id": run["run_id"],
            },
            queue=get_next_queue("saving_queue"),
        )
    logger.info("Workflow chain started")
    logger.debug("Leaving process_run task")
    return workflow_lazy_chain_that_returns_output_task_id.task_id


def get_evaluations_group(input_payload, evaluations, run_id, engagement_name):
    """Returns lazy chord"""
    logger.debug("Entering get_evaluations_group function")
    evaluation_tasks = [
        evaluate.s(input_payload, evaluations[i], run_id, engagement_name).set(queue=get_next_queue("evaluation_queue"))
        for i in range(len(evaluations))
    ]
    evaluations_group = group(evaluation_tasks)
    logger.debug("Leaving get_evaluations_group function")
    return chord(evaluations_group)


@celery_app.task
def publish_exception_to_pubsub(data):
    if topic_path:
        log_data = {"env": os.getenv("ENVIRONMENT", "development"), "data": data}
        future = publisher.publish(topic_path, json.dumps(log_data).encode("utf-8"))

        def callback(future):
            try:
                message_id = future.result()
                logger.info(
                    f"Published exception to Pub/Sub with message ID: {message_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish exception to Pub/Sub: {e}", exc_info=True
                )

        future.add_done_callback(callback)
