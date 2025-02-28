import json
import logging
import os
import sys
import threading

import json_logging
from celery import current_task

# Configure Celery logging
from celery.signals import setup_logging

# Check if JSON logging should be enabled
ENABLE_JSON_LOGGING = os.environ.get("ENABLE_JSON_LOGGING", "false").lower() == "true"

if ENABLE_JSON_LOGGING:
    json_logging.init_non_web(enable_json=True)
    if "fastapi" in sys.modules:
        json_logging.init_fastapi()

# Define log formats
JSON_LOG_FORMAT = "%(message)s"
STANDARD_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Choose the appropriate log format
log_format = JSON_LOG_FORMAT if ENABLE_JSON_LOGGING else STANDARD_LOG_FORMAT

# Configure the root logger
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# Create a logger instance for your application
logger = logging.getLogger("llm-as-evaluator")
logger.setLevel(logging.DEBUG)


# Custom JSON Formatter to include Celery task ID
class CeleryAwareJSONFormatter(json_logging.JSONLogFormatter):
    def format(self, record):
        # Manually format the log record as JSON

        log_object = {
            "message": record.getMessage(),
            "logger": record.name,
            "level": record.levelname,
            "timestamp": self.formatTime(record, self.datefmt),
            "module": record.module,
            "line_no": record.lineno,
            "thread": record.threadName,
        }

        # Add Celery task ID if available
        task = current_task
        if task and task.request:
            log_object["celery_task_id"] = task.request.id

        # Add extra fields
        if hasattr(record.getMessage(), "extra"):
            log_object.update(record.extra)

        return json.dumps(log_object)

    def formatTime(self, record, datefmt=None):
        # Override the formatTime method to format time as ISO8601
        return logging.Formatter.formatTime(
            self, record, datefmt or "%Y-%m-%dT%H:%M:%S.%fZ"
        )


if ENABLE_JSON_LOGGING:
    # Use the custom formatter for all handlers
    celery_aware_formatter = CeleryAwareJSONFormatter()
    for handler in logging.root.handlers:
        handler.setFormatter(celery_aware_formatter)


@setup_logging.connect
def setup_celery_logging(**kwargs):
    if ENABLE_JSON_LOGGING:
        # Remove existing handlers
        logging.root.handlers = []

        # Add a new handler with appropriate formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CeleryAwareJSONFormatter())
        logging.root.addHandler(handler)

    # Set the log level
    logging.root.setLevel(logging.DEBUG)


# Function to check if JSON logging is enabled
def is_json_logging_enabled():
    return ENABLE_JSON_LOGGING


class ContextFilter(logging.Filter):
    def __init__(self, name=""):
        super().__init__(name)
        self.local = threading.local()

    def filter(self, record):
        record.thread_name = getattr(self.local, "thread_name", "MainThread")
        record.message_id = getattr(self.local, "message_id", "N/A")
        return True

    def set_context(self, thread_name=None, message_id=None):
        if thread_name:
            self.local.thread_name = thread_name
        if message_id:
            self.local.message_id = message_id

    def clear_context(self):
        self.local.thread_name = "MainThread"
        self.local.message_id = "N/A"


context_filter = ContextFilter()
worker_logger = logging.getLogger("worker")
worker_logger.setLevel(logging.DEBUG)  # Set DEBUG level for the worker logger
worker_logger.addFilter(context_filter)

# Define a custom formatter for the worker logger
worker_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(thread_name)s - %(message_id)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)

# Create a handler for the worker logger
worker_handler = logging.StreamHandler(sys.stdout)
worker_handler.setFormatter(worker_formatter)
worker_logger.addHandler(worker_handler)

# Remove any default handlers from the worker logger
worker_logger.propagate = False


def set_log_context(message_id=None, thread_name=None):
    if message_id and thread_name:
        context_filter.set_context(thread_name=thread_name, message_id=message_id)
    elif message_id:
        context_filter.set_context(message_id=message_id)
    elif thread_name:
        context_filter.set_context(thread_name=thread_name)


def clear_log_context():
    context_filter.clear_context()
