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


class UnifiedTextFieldGrammarEvaluator(SingleStageMessagesEvaluator):

    class InputSchema(BaseModel):
        text: Any = Field(..., description="Content to be checked for English errors")

    class LanguageIssues(BaseModel):
        """Output for the text evaluation"""

        list_of_language_mistakes: str = Field(
            ...,
            description="List of *language* mistakes found in the provided TEXT in markdown format.",
        )
        evaluation_result: str = Field(
            ...,
            description="FAIL if there are any, even one, *language* mistakes and PASS otherwise.",
        )
        total_number_of_errors: int = Field(
            ..., description="Total number of language errors found in the text."
        )

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False,
    ):
        r = None
        for _ in range(2):
            eval_result = super().evaluate(
                input_data, config, input_validation, parse, format_to_issues_scores
            )
            gevent.sleep(0)
            if not eval_result:
                logger.warning(
                    "Evaluation result is False, skipping further processing."
                )
                continue
            r = eval_result["result"].get("text", "")
            if r and "TOTAL ERRORS:" in r:
                try:
                    parts = r.split("TOTAL ERRORS:")
                    if len(parts) == 2:
                        total_errors_str = parts[-1].strip()
                        list_of_language_mistakes = parts[0].strip()
                        total_number_of_errors = int(total_errors_str)
                        logger.info(
                            "Extracted total number of errors: %d",
                            total_number_of_errors,
                        )
                        break
                except ValueError as e:
                    logger.error(
                        "Error parsing total number of errors from result.",
                        exc_info=True,
                    )
                    raise e
        else:
            logger.error(
                "Failed to find 'TOTAL ERRORS:' in the evaluation result after 2 attempts."
            )
            raise Exception("Evaluation failed to find 'TOTAL ERRORS:' in the result.")

        r = {
            "result": {
                "list_of_language_mistakes": list_of_language_mistakes,
                "evaluation_result": "PASS" if total_number_of_errors == 0 else "FAIL",
                "total_number_of_errors": total_number_of_errors,
            },
            "metadata": eval_result["metadata"],
        }
        return r
