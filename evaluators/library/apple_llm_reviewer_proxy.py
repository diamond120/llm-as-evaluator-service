import os
import re
from abc import ABC, abstractmethod
from typing import Any

import gevent
import requests
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel, Field

from app.logging_config import logger
from common.exceptions import ValidationException
from common.utils import load_env, num_tokens_from_string
from evaluators.evaluator_base import BaseEvaluator
from evaluators.library.single_stage_messages import SingleStageMessagesEvaluator


def parse_config(config):
    """Parses the config to extract and update the language value from the quality_aspect string."""
    quality_aspect = config.get("quality_aspect", "")
    match = re.search(r"@([^@]+)@", quality_aspect)
    if match:
        language = match.group(1)
        # Remove the found language along with @@ from quality_aspect
        config["quality_aspect"] = quality_aspect.replace(f"@{language}@", "")
        # Update the config with the extracted language
        config["language"] = language
    else:
        config["language"] = "python"
    return config


def request_review(input_data, config):
    try:
        # Extract input data
        collab_id = input_data.get("colab_id")
        collab_revision = input_data.get("colab_revision")
        user_email = input_data.get("user_email")

        # Extract language from config
        language = config["language"]

        # Get the API key from environment variables
        api_key = os.getenv("APPLE_LLM_REVIEWER_API_KEY")
        if not api_key:
            logger.error("API key for Apple LLM Reviewer is missing.")
            raise EnvironmentError(
                "API key for Apple LLM Reviewer is not set in environment variables."
            )

        headers = {"Content-Type": "application/json", "x-api-key": api_key}

        # Make the initial request to start the review
        review_url = "https://llm-reviewer.xxxx.com/api/v1/review_collab"
        review_data = {
            "collab_id": collab_id,
            "language": language,
            "email": user_email,
        }
        logger.debug(
            "Sending review request to URL: %s with data: %s", review_url, review_data
        )
        response = requests.post(review_url, headers=headers, json=review_data)
        response.raise_for_status()
        response_data = response.json()

        # Extract task_id from the response
        task_id = response_data["data"]["task_id"]
        logger.info("Review task initiated with task_id: %s", task_id)
        gevent.sleep(10)
        # Poll the status endpoint every 5 seconds
        status_url = "https://llm-reviewer.xxxx.com/api/v1/review_collab/status"
        status_data = {"collab_id": collab_id}
        while True:
            logger.debug("Polling status for collab_id: %s", collab_id)
            status_response = requests.get(
                status_url, headers=headers, json=status_data
            )
            status_response.raise_for_status()
            status_response_data = status_response.json()
            status = status_response_data["data"]["status"]

            if status == "done":
                logger.info("Review status changed to: %s", status)
                break
            elif status == "error":
                logger.error(
                    "Review process encountered an error with status: %s", status
                )
                raise Exception("Review process encountered an error.")
            gevent.sleep(5)

        # Construct the result URL
        review_url = f"https://llm-reviewer.xxxx.com/colabs/{collab_id}/reviews"
        logger.info("Review completed. Access results at: %s", review_url)

        url_result = "https://llm-reviewer.xxxx.com/api/v1/review_collab/results"

        response_result = requests.get(url_result, headers=headers, json=status_data)
        response_result.raise_for_status()
        result_data = response_result.json()

        return {
            "url": f"**Review URL**: [{review_url}]({review_url})",
            "result": result_data,
        }

    except requests.exceptions.RequestException as e:
        logger.error(
            "Network-related error occurred during the review process.", exc_info=e
        )
        raise Exception(
            "Failed to communicate with the review service due to a network error."
        ) from e
    except KeyError as e:
        logger.error("Expected key missing in the response data: %s", e, exc_info=True)
        raise ValueError(f"Missing expected key in response data: {e}") from e
    except Exception as e:
        logger.error(
            "An unexpected error occurred in the review process.", e, exc_info=True
        )
        raise Exception(
            "An unexpected error occurred during the review process."
        ) from e


class AppleLLMReviewerProxy(BaseEvaluator):

    scoring_messages = [
        [
            "system",
            """You are an expert at scoring a task based on found issues.

Please follow the outlined scoring rules and evaluate the provided list of turns and issues:
<|SCORING RULES START|>
{scoring_rules}
<|SCORING RULES END|>

Show your step by step process in the `before_scoring` field.
DO NOT COPY PASTE PROVIDED DATA. THINK.
""",
        ],
        [
            "human",
            """Here are the issues found in the task during its review:

<|FOUND ISSUES START|>
{review_results}
<|FOUND ISSUES START|>
Please, proceed to score the review now!
""",
        ],
    ]

    class ScoringInputConfig(BaseModel):
        review_results: Any = Field(
            ..., description="Dictionary containing the results of the review process."
        )
        scoring_rules: Any = Field(
            ...,
            description="Dictionary defining the rules for scoring the review results.",
        )

    class ScoringOutput(BaseModel):
        """Score output"""

        before_scoring: str = Field(
            ..., description="Place to output your step by step scoring process."
        )
        score: int = Field(
            ..., description="Final score ranging from 1 to 5.", ge=1, le=5
        )
        short_issues_summary_md: str = Field(
            ...,
            description="A brief markdown scoing explanation without deep details. USE STRUCTURED MARKDOWN.",
        )

    def __init__(
        self,
        name: str,
        config: dict,
        llm_config: dict,
        config_schema: dict,
        input_schema: dict,
        output_schema: dict,
        config_validation: bool = True,
        run_id: int | None = None,
        engagement_name: str = "",
    ):
        super().__init__(
            name,
            config,
            llm_config,
            config_schema,
            input_schema,
            output_schema,
            config_validation,
            run_id=run_id,
            engagement_name=engagement_name,
        )

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False,
    ):
        if input_validation:
            self.validate_input({**input_data, **config})

        # Call the function with the input data and config
        config = parse_config(config)
        result = request_review(input_data, config)
        issues = [result["url"]]
        reviews = result["result"].get("data", {}).get("reviews", [])
        processed_reviews = [
            {"turn": review.get("turn"), "issues": review.get("fix")}
            for review in reviews
        ]
        scoring_evaluator = SingleStageMessagesEvaluator(
            "scoring_" + self.name,
            {
                "messages": self.scoring_messages,
                "retries": self.config.get("retries", 3),
            },
            self.llm_config,
            SingleStageMessagesEvaluator.ConfigSchema.model_json_schema(),
            self.ScoringInputConfig.model_json_schema(),
            output_schema=self.ScoringOutput.model_json_schema(),
        )
        score_out = scoring_evaluator.evaluate(
            {
                "review_results": processed_reviews,
                "scoring_rules": config["quality_aspect"],
            },
            config,
            parse=parse,
            input_validation=input_validation,
        )

        r = {
            "result": {
                "issues": issues + [score_out["result"]["short_issues_summary_md"]],
                **score_out["result"],
            },
            "metadata": score_out["metadata"],
        }
        return r
