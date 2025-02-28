import os
from typing import Any

import tiktoken
from dotenv import find_dotenv, load_dotenv

openai_encoding = tiktoken.get_encoding("cl100k_base")


def load_env(override: bool = True) -> dict:
    load_dotenv(find_dotenv(), override=override)
    env_vars = {key: os.getenv(key) for key in os.environ}
    if "TLT_API_USERS" in env_vars:
        env_vars["TLT_API_USERS"] = [
            email.strip() for email in env_vars["TLT_API_USERS"].split(",")
        ]
    return env_vars


def num_tokens_from_string(obj: Any) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = len(openai_encoding.encode(str(obj)))
    return num_tokens


def get_next_queue(queue, is_bulk_request=False):
    if is_bulk_request or os.getenv("BULK_REQUEST"):
        return f"bulk_{queue}"
    return queue
