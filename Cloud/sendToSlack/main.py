import base64
import json
import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


slack_token = os.getenv("SLACK_TOKEN")
channel_id = os.getenv("CHANNEL_ID")  # Get CHANNEL_ID from env - deploy script
file_path = "/tmp/alerts.txt"
logger = logging.getLogger(__name__)
client = WebClient(token=slack_token)


def publish_to_slack(event, context):
    pubsub_message = base64.b64decode(event["data"]).decode("utf-8")

    message_data = json.loads(pubsub_message)
    logger.info(f"Message data: {message_data}")

    traceback = message_data["data"].get("traceback", [])
    if not isinstance(traceback, list):
        traceback = [traceback]

    evaluator_names = message_data["data"].get("name", [])
    if not isinstance(evaluator_names, list):
        evaluator_names = [evaluator_names]

    lines = [
        f"ENV: {message_data['env']}\n",
        f"RUN_ID: {message_data['data'].get('run_id')}\n\n",
    ]

    for evaluator_name, tb in zip(evaluator_names, traceback):
        lines.append(f"{evaluator_name}\n")
        lines.append(f"{tb}\n")
        lines.append(
            "=======================================================================================\n\n"
        )

    # Open the file in write mode ('w')
    with open(file_path, "w") as file:
        # Write each line to the file
        file.writelines(lines)

    try:
        result = client.files_upload_v2(
            channel=channel_id,
            initial_comment="Run failed",
            file=file_path,
        )
        # Log the result
        logger.info(result)

    except SlackApiError as e:
        logger.error("Error uploading file: {}".format(e))
