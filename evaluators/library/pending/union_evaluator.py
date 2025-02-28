import concurrent.futures
import json
import os
from abc import abstractmethod
from typing import Any, List, Optional

from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.prompts.base import BasePromptTemplate
from langchain.pydantic_v1 import BaseModel, Field
from langchain_anthropic.output_parsers import (
    ToolsOutputParser as AntrhropicToolsOutputParser,
)
from langchain_core.output_parsers.format_instructions import JSON_FORMAT_INSTRUCTIONS
from langchain_core.output_parsers.json import parse_json_markdown
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from llm_failover import ChatFailoverLLM

from app.logging_config import logger
from common.utils import load_env
from evaluators.evaluator_base import BaseEvaluator
from evaluators.formatter_to_issues import format_output_to_issues
from evaluators.library.echo import EchoSingleStageMessagesEvaluator
from evaluators.library.single_stage_messages import SingleStageMessagesEvaluator


class UnionEvaluator(BaseEvaluator):
    def __init__(
        self,
        name,
        config,
        llm_config,
        config_schema,
        input_schema,
        output_schema,
        run_id=None,
        engagement_name="",
    ):
        super().__init__(
            name,
            config,
            llm_config,
            config_schema,
            input_schema,
            output_schema,
            run_id=run_id,
            engagement_name=engagement_name,
        )

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        format_to_issues_scores=False,
        parse=None,
    ):

        logger.info("Starting evaluation...")

        if input_validation:
            logger.info("Validating input data...")
            self.validate_input({**input_data, **config})

        cell_output = evaluate_text(text, parse=False if parse is False else True)
        if format_to_issues_scores:
            return self.format_output_to_issues(grammar_out)
        else:
            return grammar_out


def evaluate_text(
    text,
    first_stage_params_list,
    first_stage_prompt,
    final_output_prompt,
    final_output_schema,
    final_output_params,
    parse=True,
):
    try:
        # First model invocation to find grammar mistakes
        chat_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Find all **grammar** mistakes, ingore all other mistakes and issues. If it's code, judge it well, shortcuts are ok but blatant misspelling is not. Example: def Ornge() is ok but Oringe() is not. ONLY OUTPUT CORRECTIONS, DO NOT COPY WHOLE TEXT",
                ),
                ("user", "<|RAW TEXT START|>{text}<|RAW TEXT END|>"),
            ]
        )

        def invoke_model(template, params):
            model = ChatFailoverLLM(
                initial_provider="openai_api",
                initial_model="gpt-4o",,
                **params,
                streaming=False,
            ).with_retry(stop_after_attempt=2)
            return (template | model).invoke({"text": text}).content

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(invoke_model, chat_template, params)
                for params in first_stage_params_list
            ]
            results = [future.result() for future in futures]

        if all(result is None for result in results):
            raise Exception("All model invocations failed.")
        combined_result = [result for result in results if result is not None]

        # Second model invocation to convert to JSON as per schema
        chat_template2 = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Convert this text into the proper JSON as specified by schema. Text consists out of multiple variants of the issues for the same original text. Remove any duplicates or places where "where" equals to "fix". The aim of the input text is to fix **grammar** mistakes only, if no mistake is present, discard. So, if it says there is a mistake but you don't see it being fixed, discard!""",
                ),
                ("user", "<|RAW TEXT START|>{combined_result}<|RAW TEXT END|>"),
            ]
        )
        model2 = ChatFailoverLLM(
            initial_provider="openai_api",
            initial_model="gpt-4o",
            **{"temperature": 0, "seed": 4123, "max_tokens": 800},
            streaming=False,
        )
        model2 = model2.bind_tools(
            [final_output_schema],
            tool_choice={
                "type": "function",
                "function": {"name": final_output_schema["title"]},
            },
        )
        if parse:
            r = (
                (chat_template2 | model2 | JsonOutputToolsParser())
                .with_retry(stop_after_attempt=3)
                .invoke({"combined_result": combined_result})
            )
        else:
            r = (
                (chat_template2 | model2)
                .with_retry(stop_after_attempt=3)
                .invoke({"combined_result": combined_result})
            )
        return r
    except Exception as e:
        logging.error(f"Text processing failed: {e}", exc_info=True)
        return None
