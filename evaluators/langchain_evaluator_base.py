import json
import os
from abc import abstractmethod
from typing import Any

import gevent
from langchain.prompts import HumanMessagePromptTemplate
from langchain.prompts.base import BasePromptTemplate
from langchain.schema import AIMessage, ChatGeneration
from langchain_core.output_parsers.format_instructions import \
    JSON_FORMAT_INSTRUCTIONS
from langchain_core.output_parsers.json import parse_json_markdown
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_core.output_parsers.string import StrOutputParser
from llm_failover import ChatFailoverLLM

from app.logging_config import logger
from common.utils import load_env
from evaluators.evaluator_base import BaseEvaluator
from evaluators.formatter_to_issues import format_output_to_issues
from evaluators.gcs_utils import get_gsc_images_as_data_urls
from evaluators.mixins import TokenUsageMixin


def StructuredOutputParser(ai_message) -> dict:
    parsed = ai_message["parsed"]
    if isinstance(parsed, list):
        return parsed[0]["args"]
    return parsed


class LangChainBaseEvaluator(BaseEvaluator, TokenUsageMixin):

    @abstractmethod
    def create_prompt(self, input_data) -> BasePromptTemplate:
        pass

    def create_model(self):
        params = self.llm_config["params"]
        if self.engagement_name.lower() == "apple":
            api_key = os.getenv("OPEN_AI_APPLE_KEY")
            if api_key:
                params["initial_key"] = api_key
            else:
                logger.warning(
                    "No API key found for 'apple' engagement in environment variables(OPEN_AI_APPLE_KEY). Routing to usual flow."
                )

        return ChatFailoverLLM(
            initial_provider=self.llm_config["provider"],
            initial_model=self.llm_config["model"],
            **params,
            streaming=False,
        )

    def _instruct_for_json_output(self, prompt):
        logger.debug(
            f"Adding JSON format instructions to the prompt. run_id: {self.run_id}"
        )
        prompt.messages[0].prompt = (
            prompt.messages[0].prompt
            + (JSON_FORMAT_INSTRUCTIONS.format(schema=self.output_schema))
            .replace("{", "{{")
            .replace("}", "}}")
            + "\nPlease, output only JSON nothing else, start with {{"
        )
        return prompt

    def _instruct_for_json_output_always_choose_a_tool(self, prompt, tool_name):
        logger.debug(
            f"Adding tool-specific JSON format instructions to the prompt for tool: {tool_name}. run_id: {self.run_id}"
        )
        prompt.messages[0].prompt = (
            prompt.messages[0].prompt
            + f"\nPlease, output only JSON nothing else, use the tool {tool_name}!"
        )
        return prompt

    def prepare_for_tool_use(self, prompt, model):
        provider = self.llm_config["provider"]
        logger.debug(
            f"Preparing for tool use with provider: {provider}, run_id: {self.run_id}"
        )
        return prompt, model.with_structured_output(self.output_schema, include_raw=True), StructuredOutputParser, "json"

    def add_images_to_prompt(self, prompt, gcs_images_list):
        """gcs_images_list = [{'uri': 'gcs://...', params: {'detail': 'auto'}}]"""
        uris = [item["uri"] for item in gcs_images_list]
        images = get_gsc_images_as_data_urls(uris)

        # Combine images back with their respective params
        images = [
            {"type": "image_url", "image_url": {"url": image, **item["params"]}}
            for item, image in zip(gcs_images_list, images)
        ]
        human_messages = [
            (index, message)
            for index, message in enumerate(prompt.messages)
            if isinstance(message, HumanMessagePromptTemplate)
        ]
        if human_messages:
            prompt.messages[human_messages[-1][0]] = (
                HumanMessagePromptTemplate.from_template(
                    template=[
                        {"type": "text", "text": human_messages[-1][1].prompt.template}
                    ]
                    + images
                )
            )
        else:
            prompt.messages.append(
                HumanMessagePromptTemplate.from_template(
                    template=[
                        {
                            "type": "text",
                            "text": "Here are the images for you to look at.",
                        }
                    ]
                    + images
                )
            )

        return prompt

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=None,
        format_to_issues_scores=False,
    ):
        if parse is None:
            parse = True
        input_data = {**input_data, **config}
        if input_validation:
            logger.debug(f"Validating input data. run_id: {self.run_id}")
            self.validate_input(input_data)

        prompt = self.create_prompt(input_data)

        model = self.create_model()

        if self.output_schema:
            prompt, model, output_parser, output_type = self.prepare_for_tool_use(
                prompt, model
            )
        else:
            output_parser = StrOutputParser()
            output_type = "text"
        if "__add_images_list_gcs" in input_data:
            prompt = self.add_images_to_prompt(
                prompt, input_data["__add_images_list_gcs"]
            )

        result = self._execute_chain(
            prompt, model, input_data, parse, output_parser, output_type
        )

        if parse:
            if output_type == "tool":
                res = (
                    result["result"][0]["args"]
                    if isinstance(result["result"], list)
                    else result["result"]
                )
            elif output_type == "json":
                res = result["result"]
            elif output_type == "text":
                if isinstance(result["result"], AIMessage):
                    res = {"text": result["result"].content}
                else:
                    res = {"text": result["result"]}
            else:
                logger.error(
                    f"Wrong output type in evaluate: {output_type}, run_id: {self.run_id}"
                )
                raise NotImplementedError(
                    f"Wrong output type in evaluate {output_type}"
                )

            if format_to_issues_scores:
                formatted_res = format_output_to_issues(res)
                return {"metadata": result["metadata"], "result": formatted_res}
            else:
                return {"metadata": result["metadata"], "result": res}

        else:
            return result

    def _execute_chain(
        self, prompt, model, input_data, parse, output_parser, output_type
    ):
        retries = self.config.get("retries", 3)
        total_metadata = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        for attempt in range(retries):
            try:
                gevent.sleep(0)
                chain = prompt | model
                raw_result = chain.invoke(input_data)

                # check if structured output is used
                metadata = self.extract_token_usage(raw_result["raw"] if "raw" in raw_result else raw_result)

                # Aggregate metadata
                for key in total_metadata:
                    total_metadata[key] += metadata.get(key, 0)

                if parse:
                    parsed_result = self._parse_result(
                        raw_result, output_parser, output_type
                    )
                else:
                    parsed_result = {"RAW_OUTPUT": str(raw_result)}

                return {"metadata": total_metadata, "result": parsed_result}
            except Exception as e:
                gevent.sleep(0)
                logger.error(
                    f"Attempt {attempt + 1} of {retries} failed with error: {e}, run_id: {self.run_id}",
                    exc_info=True,
                )
                if attempt == retries - 1:
                    raise

    def _parse_result(self, raw_result, output_parser, output_type):
        if output_parser is None:
            return raw_result.content if hasattr(raw_result, "content") else raw_result

        if isinstance(output_parser, JsonOutputToolsParser):
            # JsonOutputToolsParser expects a list of ChatGeneration objects
            if isinstance(raw_result, AIMessage):
                chat_generation = ChatGeneration(message=raw_result)
                return output_parser.parse_result([chat_generation])
            else:
                # If it's not an AIMessage, wrap it in an AIMessage and ChatGeneration
                ai_message = AIMessage(content=str(raw_result))
                chat_generation = ChatGeneration(message=ai_message)
                return output_parser.parse_result([chat_generation])

        elif callable(output_parser):  # This covers StructuredOutputParser
            return output_parser(raw_result)

        else:
            # For any other type of parser, try to use its parse method
            try:
                return output_parser.parse(raw_result)
            except AttributeError:
                raise ValueError(
                    f"Unsupported output parser type: {type(output_parser)}, run_id: {self.run_id}"
                )
