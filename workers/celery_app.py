import logging
import os

from celery import Celery

from common.utils import load_env


env_vars = load_env()
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
backend_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

logging.info(f"Configured Redis broker URL: {broker_url}")
logging.info(f"Configured Redis backend URL: {backend_url}")


celery_app = Celery(
    "workers",
    broker=broker_url,
    backend=backend_url,
    include=["workers.slim_tasks"],
)

celery_app.conf.update(
    task_routes={
        "workers.celery_app.process_run": {"queue": "process_queue"},
        "workers.celery_app.fail_run": {"queue": "process_queue"},
        "workers.celery_app.fail_run_on_save_error": {"queue": "process_queue"},
        "workers.celery_app.save_results": {"queue": "saving_queue"},
        "workers.celery_app.evaluate": {"queue": "evaluation_queue"},
        "workers.celery_app.stage2_evaluate": {"queue": "evaluation_stage2_queue"},
        "workers.celery_app.compile_evaluations": {"queue": "db_fetch_queue"},
        "workers.celery_app.convert_results_to_dict": {"queue": "evaluation_queue"},
        "workers.celery_app.evaluate_workflow": {"queue": "evaluation_queue"},
        "workers.celery_app.prepare_output_for_saving": {"queue": "evaluation_queue"},
        "workers.celery_app.process_webhook_data": {"queue": "webhook_queue"},
    },
    # broker_pool_limit=0,  # Disable connection pool for the broker
    worker_concurrency=25,  # Number of concurrent worker processes/threads for I/O bound tasks
    # worker_pool="gevent",  # Use gevent pool for handling I/O bound tasks
    task_acks_late=True,  # Ensure tasks are acknowledged only after execution
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=5000,  # Recycle each worker after 5000 tasks
    worker_prefetch_multiplier=1,  # Prefetch one task at a time
    enable_utc=True,
    task_time_limit=1500,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    celery_create_missing_queues=True,
)
