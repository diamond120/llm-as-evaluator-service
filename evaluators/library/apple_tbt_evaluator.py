from abc import abstractmethod
from enum import Enum
from typing import Any, Optional

import gevent
from gevent import Greenlet
from gevent.pool import Pool
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from app.logging_config import logger
from common.utils import load_env
from evaluators.formatter_to_issues import format_output_to_issues
from evaluators.library.cbc_two_stage import CBCTwoStageEvaluator
from evaluators.library.generic_scoring_prompt import (
    SCORING_MESSAGES_PROMPT,
    ScoringOutput,
)
from payload_parsers.apple_turn_constructor import parse_payload


class AppleTurnByTurnEvaluator(CBCTwoStageEvaluator):

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False,
    ):
        original_count = len(input_data["conversation"])
        conversation = parse_payload(input_data["conversation"])["conversation"]
        filtered_conversation = [
            (idx + 1, c)
            for idx, c in enumerate(conversation)
            if c.get(self.config["focus_on_field"])
        ]
        filtered_count = len(filtered_conversation)

        logger.info(
            "Original conversation count: %d, Filtered conversation count: %d",
            original_count,
            filtered_count,
        )

        input_data = {
            **input_data,
            "conversation": [c for _, c in filtered_conversation],
        }

        if "@@@" in config.get("quality_aspect", ""):
            language = config["quality_aspect"].split("@@@")[-1]
            config["language"] = language
            logger.info("Language set to: %s", language)
        else:
            logger.info("No language specified in quality_aspect")
        self.config["messages"] = SCORING_MESSAGES_PROMPT
        self.output_schema = ScoringOutput.model_json_schema()
        r = super().evaluate(
            input_data, config, input_validation, parse, format_to_issues_scores=False
        )
        if format_to_issues_scores:
            filtered_issues = []
            for (original_id, _), item in zip(
                filtered_conversation, r["result"]["multi_outputs"]
            ):
                if isinstance(item, dict) and "text" in item:
                    if (
                        not (
                            item["text"].strip().lower() in ["no issues", "no issues."]
                        )
                        and item["text"].strip()
                    ):
                        filtered_issues.append(
                            {
                                "turn": original_id,
                                "issues": [
                                    f"**Turn {original_id}:**\n\n"
                                    + item["text"].strip()
                                ],
                            }
                        )
                else:
                    filtered_issues.append(
                        {
                            "turn": original_id,
                            **format_output_to_issues(filtered_issues[-1]),
                        }
                    )
            score = 5
            logger.debug("Apple evaluator output:" + str(r))
            if "stage2_output" in r["result"]:
                score = r["result"]["stage2_output"]["score"]
            r = {
                "result": {
                    "issues": filtered_issues,
                    "score": score,
                    "whole_conversation": False,
                },
                "metadata": r["metadata"],
            }
        return r
