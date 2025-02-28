import json
import os
from json import JSONEncoder

from mistralai import Mistral
from openai import OpenAI

from evaluators.evaluator_base import BaseEvaluator


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)


class OpenAIEvaluator(BaseEvaluator):
    def __init__(
        self,
        name,
        config,
        llm_config,
        config_schema,
        input_schema,
        output_schema,
        config_validation=True,
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
            config_validation,
            run_id=run_id,
            engagement_name=engagement_name,
        )
        self.client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
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
            self.validate_input(input_data)

        messages = input_data["messages"]
        print("llm_config", self.llm_config)
        try:
            model = self.llm_config.get("model")
            tools = input_data.get("tools", [])
            tool_choice = input_data.get("tool_choice", "auto")
            if not model:
                raise ValueError("Model parameter is missing in the configuration.")
            response = self.client.chat.completions.create(
                messages=messages,
                model=model,
                tools=tools if tools else None,
                tool_choice=tool_choice,
            )
        except Exception as e:
            error_message = f"An error occurred in passthrough_openai: {e}"
            raise ValueError(error_message)
        return self.serialize_response(response)

    def serialize_response(self, response):
        return json.dumps(response, cls=CustomJSONEncoder, ensure_ascii=False, indent=2)


class MistralEvaluator(BaseEvaluator):
    def __init__(
        self,
        name,
        config,
        llm_config,
        config_schema,
        input_schema,
        output_schema,
        config_validation=True,
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
            config_validation,
            run_id=run_id,
            engagement_name=engagement_name,
        )
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

    def evaluate(self, input_data, config, input_validation=True):
        if input_validation:
            self.validate_input(input_data)

        messages = input_data["messages"]
        model = self.llm_config.get("model", "mistral-large-latest")
        tools = input_data.get("tools", [])
        tool_choice = input_data.get("tool_choice", "auto")

        response = self.client.chat.complete(
            model=model,
            messages=messages,
            tools=tools if tools else None,
            tool_choice=tool_choice,
        )

        return self.serialize_response(response)

    def serialize_response(self, response):
        return json.dumps(response, cls=CustomJSONEncoder, ensure_ascii=False, indent=2)
