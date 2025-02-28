import json
from enum import Enum
from typing import Any

from google.cloud import pubsub_v1
from google.oauth2 import service_account
from pydantic import BaseModel, Field

from common.constants import GOOGLE_API_CREDENTIALS_PATH
from common.utils import load_env

env_vars = load_env()

PROJECT_ID = env_vars["GOOGLE_CLOUD_PROJECT"]
TOPIC_ID = env_vars["PUBSUB_TOPIC"]


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


class PubSubMessage(BaseModel):
    evaluation_id: int = Field(...)
    input: Any = Field(...)
    input_type: str = Field(...)
    stage1_ids: list[int] | None = Field(
        default=None, description="Stage 1 evaluation ids"
    )
    stage2_ids: list[int] | None = Field(
        default=None, description="Stage 2 evaluation ids"
    )
    is_dev: bool = Field(default=False)
    aux_params: dict | None = None

    def serialize(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def deserialize(cls, message: bytes) -> "PubSubMessage":
        return cls(**json.loads(message.decode("utf-8")))


def create_stage_pubsub_messages(
    evaluation_ids,
    input_data,
    input_type,
    stage2_eval_ids,
    is_dev=False,
    parse=None,
    format_to_issues_scores=None,
):
    messages = []
    aux_params = None
    if parse is not None or format_to_issues_scores is not None:
        aux_params = {
            "parse": parse if parse is not None else None,
            "format_to_issues_scores": (
                format_to_issues_scores
                if format_to_issues_scores is not None
                else False
            ),
        }
    # for eval_id in evaluation_ids:
    #     message = PubSubMessage(
    #         evaluation_id=eval_id,
    #         input=input_data,
    #         input_type=input_type,
    #         stage2_ids=stage2_eval_ids,
    #         is_dev=is_dev,
    #         aux_params=aux_params,
    #     )
    #     messages.append(message)

    # return messages

    message = PubSubMessage(
        evaluation_id=evaluation_ids[0],  # todo: this can be removed in future
        input=input_data,
        input_type=input_type,
        stage1_ids=evaluation_ids,
        stage2_ids=stage2_eval_ids,
        is_dev=is_dev,
        aux_params=aux_params,
    )
    return [message]


def publish_messages(messages):
    """
    Publishes a list of serialized PubSubMessage objects to a Pub/Sub topic.

    :param messages: List of serialized PubSubMessage objects.
    """
    # Load environment variables

    # Initialize Pub/Sub publisher client with credentials
    import time

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_API_CREDENTIALS_PATH
    )

    publisher = pubsub_v1.PublisherClient(credentials=credentials)

    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

    futures = []
    for message in messages:
        future = publisher.publish(topic_path, message.serialize())
        futures.append(future)

    for future in futures:
        future.result()
