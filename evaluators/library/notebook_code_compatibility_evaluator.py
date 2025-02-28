import json, requests
import gevent
from gevent.pool import Pool
from concurrent.futures import ThreadPoolExecutor
import re
from evaluators.library import CBCTwoStageEvaluator
import os
import datetime
import io
import uuid
import shutil
from google.cloud import storage
from evaluators.gcs_utils import (
    get_google_drive_service,
    download_all_files_in_folder,
    find_folder_id_by_path,
    CloudStorageManager,
)
import dotenv
from app.logging_config import logger
from evaluators.formatter_to_issues import format_output_to_issues

dotenv.load_dotenv(dotenv.find_dotenv(), override=True)


def create_files_payload(
    COLAB_ID,
    BATCH_ID,
    service,
    DRIVE_ID="0AEueUZbGtaKXUk9PVA",
    destination_folder="downloads",
):
    path_in_drive = os.path.join(BATCH_ID, COLAB_ID)
    folder_id = find_folder_id_by_path(path_in_drive, DRIVE_ID, service)

    files = download_all_files_in_folder(
        folder_id, destination_folder, service, is_shared_drive=True, drive_id=DRIVE_ID
    )
    cm = CloudStorageManager()
    for file in files:
        file["url"] = cm.upload_blob_signed_url(
            os.getenv("GCS_BUCKET_NAME"), file["local_path"], "code_interpreter"
        )
        # Extract the path after COLAB_ID
        base_path = file["local_path"].split(COLAB_ID + "/")[-1].split("/", 1)[-1]
        file["path"] = os.path.join("./data/", base_path)
    return files


def get_batch_and_colab_ids(code, invalid_cells):

    if not isinstance(code, str):
        code = str(code)

    if not isinstance(invalid_cells, str):
        code = code + str(invalid_cells)

    # Regular expression patterns to find COLAB_ID and BATCH_ID
    colab_id_pattern = r"COLAB_ID = \"([^\"]+)\""
    batch_id_pattern = r"BATCH_ID = \"([^\"]+)\""

    # Search for COLAB_ID and BATCH_ID in the code
    colab_id_match = re.search(colab_id_pattern, code)
    batch_id_match = re.search(batch_id_pattern, code)

    # Extract the matched groups if found
    colab_id = colab_id_match.group(1) if colab_id_match else None
    batch_id = batch_id_match.group(1) if batch_id_match else None
    return {"COLAB_ID": colab_id, "BATCH_ID": batch_id}


def split_notebook_turns(conversation):
    turns = []
    turn = []
    for message in conversation:
        if message.get("role") == "User":
            if message:
                turns.append(turn)
            turn = [
                {
                    "role": message.get("role"),
                    "content": message.get("content"),
                    "cell_pos": message.get("cell_pos"),
                    "type": message.get("type"),
                }
            ]
        elif message.get("role") == "Assistant":
            turn.append(
                {
                    "role": message.get("role"),
                    "content": message.get("content"),
                    "cell_pos": message.get("cell_pos"),
                    "type": message.get("type"),
                }
            )
        else:
            raise ValueError(
                f"Unexpected role found in conversation. {message.get('role')}"
            )
    if turn:
        turns.append(turn)

    return turns


def extract_assistant_code_cells(notebook):
    in_turns = split_notebook_turns(notebook)
    grouped_code = []
    for turn in in_turns:
        code_cells = ""
        for entry in turn:
            if entry.get("role") == "Assistant" and entry.get("type") == "code":
                code_cells += "\n" + entry.get("content")
        if code_cells:  # Only append if code_cells is not empty
            grouped_code.append(code_cells)
    return grouped_code


def execute_apple_code(
    instance_id, env, code, language="python3_301024_apple", files=[]
):
    # Prepare the data payload for the request
    data_payload = json.dumps(
        {"code": code, "packages": "", "input": " ", "files": files}
    )

    logger.info(f"Calling apple code with files {files}")

    # URL for the code execution server
    url = (
        f"https://code-exec-server-staging.xxxx.com/api/language/{instance_id}/execute-code"
        if env == "staging"
        else f"https://code-exec-server.xxxx.com/api/v2/language/{instance_id}/execute-code"
    )
    headers = {"Content-Type": "application/json"}
    response = None
    try:
        for attempt in range(3):  # Retry up to 2 times
            try:
                response = requests.post(
                    url, headers=headers, data=data_payload, timeout=200
                )
                if response.status_code == 200:
                    break  # Exit loop if request is successful
            except requests.exceptions.Timeout:
                gevent.sleep(0)
                if attempt < 2:
                    logger.info(
                        f"Timeout occurred, retrying... (Attempt {attempt + 1}/3)"
                    )
                    continue  # Retry if timeout occurs
                else:
                    raise  # Raise exception if all retries fail
    except Exception as e:
        logger.error(f"Failed to execute code: {str(e)}")
        return None
    if response:
        try:
            return response.json()
        except json.JSONDecodeError:
            logger.info("Failed to decode JSON from response")
            return None
    return None


def run_multiple_turns_interpreter(
    instance_id,
    env,
    drive_id,
    loaded_notebook,
    invalid_cells,
    n_workers=4,
    use_gevent=False,
):
    notebook = loaded_notebook
    service = get_google_drive_service()  # Initialize service locally
    ids = get_batch_and_colab_ids(loaded_notebook, invalid_cells)
    files = []
    if ids["BATCH_ID"] is None or ids["COLAB_ID"] is None:
        logger.warning(f"BATCH_ID or COLAB_ID is None")
        pass
    else:
        # add uuid between temp_downloads and batch id
        new_uuid = str(uuid.uuid4())
        destination_folder = os.path.join(
            "temp_downloads", ids["BATCH_ID"], ids["COLAB_ID"], new_uuid
        )
        files = create_files_payload(
            ids["COLAB_ID"],
            ids["BATCH_ID"],
            service,
            DRIVE_ID=drive_id,
            destination_folder=destination_folder,
        )

        if len(files) > 0:
            logger.info(
                os.path.join(
                    "temp_downloads", ids["BATCH_ID"], ids["COLAB_ID"], new_uuid
                )
            )
            shutil.rmtree(
                os.path.join(
                    "temp_downloads", ids["BATCH_ID"], ids["COLAB_ID"], new_uuid
                )
            )

    turns = extract_assistant_code_cells(
        notebook
    )  # Adjusted to work for loaded notebook

    final_output = []

    def process_turn_wrapper(turn):
        r = execute_apple_code(instance_id, env, turn, files=files)
        logger.info("EXEC RESULT", r)
        return {
            "execution_result": r["run"],
            "code": turn,
        }

    if use_gevent:
        pool = Pool(n_workers)
        jobs = [pool.spawn(process_turn_wrapper, turn) for turn in turns]
        pool.join(raise_error=True)
        final_output = [job.get() for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            final_output = list(executor.map(process_turn_wrapper, turns))

    return final_output


class ExecutionCompatabilityEvaluator(CBCTwoStageEvaluator):

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=None,
        format_to_issues_scores=False,
    ):

        exec_instance_id = self.config.get("exec_instance_id", "python3_301024_apple")
        exec_env = self.config.get("exec_env_id", "production")
        drive_id = self.config.get("drive_id", "0AEueUZbGtaKXUk9PVA")

        # happen here
        result = run_multiple_turns_interpreter(
            exec_instance_id,
            exec_env,
            drive_id,
            loaded_notebook=input_data["conversation"],
            invalid_cells=input_data.get("invalid_cells", ""),
        )

        filtered_results = [
            (index, turn)
            for index, turn in enumerate(result)
            if turn["execution_result"] is not None
        ]
        new_input_data = {"conversation": [turn for _, turn in filtered_results]}
        # ends here

        r = super().evaluate(
            new_input_data,
            config,
            input_validation=input_validation,
            parse=parse,
            format_to_issues_scores=False,
        )

        issues = []
        score = 5

        for idx in range(len(filtered_results)):
            if r["result"]["multi_outputs"][idx]["result"].lower() == "no":
                s = (
                    "## Code failed\n"
                    + r["result"]["multi_outputs"][idx]["comment"]
                    + "\n### Code Output\n"
                    + f"{filtered_results[idx][1]['execution_result']['out']}\n"
                    + "### Code Traceback\n"
                    + f"{filtered_results[idx][1]['execution_result']['error']}"
                )
                issues.append({"turn": filtered_results[idx][0] + 1, "issues": [s]})
                score = 1

        r["result"] = {"issues": issues, "score": score, "whole_conversation": False}
        return r
