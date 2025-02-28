from typing import Any

from pydantic import BaseModel, Field

from app.logging_config import logger
from common.exceptions import ValidationException
from evaluators.library.graph_code_checker import GraphCodeCheckerEvaluator
from evaluators.library.single_stage_messages import SingleStageMessagesEvaluator
from payload_parsers.apple_code_translation import parse_payload


def transform_input(input_dict, key_mappings):
    """
    Transform a nested dictionary into a new dictionary with specified final name fields.
    """
    output_dict = {}
    for mapping in key_mappings:
        final_name, keys = mapping.split("=")
        keys_list = keys.split(".")

        # Navigate through the nested dictionary
        value = input_dict
        for key in keys_list:
            value = value.get(key, None)
            if value is None:
                break

        # Assign the value to the new key in the output dictionary
        if value is not None:
            output_dict[final_name] = value

    return output_dict


class AppleCodeTranslationEvaluator(SingleStageMessagesEvaluator):

    class ConfigSchema(SingleStageMessagesEvaluator.ConfigSchema):

        edge_cases_count: int = Field(
            default=0,
            description="Count of edge cases, default is 0. If both edge_cases_count and happy_cases_count are zero, no tests will be generated, will be run as is.",
        )
        happy_cases_count: int = Field(
            default=0,
            description="Count of happy cases, default is 0. If both edge_cases_count and happy_cases_count are zero, no tests will be generated, will be run as is.",
        )
        prompt_params_mapping: str = Field(
            default="",
            description="String mapping for prompt parameters, used to transform input data.",
        )
        code_execution_check: bool = Field(
            default=False,
            description="If True, we will execute the code in code_to_execute_field",
        )
        number_of_edge_tests_to_generate: int = Field(
            default=0, description="Number of edge tests to generate, default is 0."
        )

    class BaseInputSchema(BaseModel):
        """Base input schema for conversation and quality aspect."""

        metadata: Any = Field(..., description="Metadata related to the conversation.")
        conversation: Any = Field(..., description="Conversation.")
        quality_aspect: str = Field(
            ..., description="Quality aspect of the conversation."
        )

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False,
    ):
        metadata = "# Metadata\n"
        ordered_keys = [
            "Prompt",
            "Keywords",
            "Difficulty Level",
            "Example",
            "Starter Code",
        ]  # Define the desired order of keys
        metadata_dict = input_data.get("metadata", {})

        # Add keys in the specified order if they exist
        for key in ordered_keys:
            if key in metadata_dict:
                metadata += f"**{key}**: {metadata_dict[key]}\n"

        # Add any new keys that are not in the specified order
        for k, value in metadata_dict.items():
            if k not in ordered_keys:
                metadata += f"**{k}**: {value}\n"
        input_data["conversation"] = parse_payload(
            [{"content": metadata, "type": "markdown"}] + input_data["conversation"]
        )
        input_data = {**input_data, **config}

        input_data.update(**self.config.get("extra_fixed_inputs_dict", {}))
        params = self.config["prompt_params_mapping"]
        if input_data["quality_aspect"].count("@@@") == 2:
            params += "\n" + input_data["quality_aspect"].split("@@@")[1]
        # if "@@@SCORING@@@" in input_data["quality_aspect"]:
        #     params, quality_aspect = input_data["quality_aspect"].split(
        #         "@@@SCORING@@@", 1
        #     )
        # else:
        #     raise ValidationException("Missing scoring section with @@@SCORING@@@.")

        print("===" * 60)
        params = "\n".join([s for s in params.strip().split("\n") if s])
        if all("=" in item for item in params.split("\n")):
            # input_data.update(dict(item.split("=", 1) for item in params.split("\n")))
            input_data.update(transform_input(input_data, params.split("\n")))
        else:
            raise ValidationException(
                f"Every line in prompt_params_mapping must contain '='. {params=}"
            )
        print(transform_input(input_data["conversation"], params.split("\n")))
        naming_conventions = {
            "swift": "Use camelCase for variable and function names.",
            "python": "Use snake_case for variable and function names.",
        }
        if (
            "language" in input_data
            and input_data["language"].lower() in naming_conventions
        ):
            input_data["naming_convention"] = naming_conventions[
                input_data["language"].lower()
            ]

        if self.config.get("code_execution_check", False):
            evaluator = GraphCodeCheckerEvaluator(
                name="Apple Translation Code evaluator",
                config={
                    "n_workers": 2,
                    "recursion_limit": 50,
                    "n_workers_inner_thread": 2,
                    "messages": [],
                    "mode": "code_string",
                },
                llm_config=self.llm_config,
                config_schema=self.ConfigSchema.model_json_schema(),
                input_schema=self.BaseInputSchema.model_json_schema(),
                output_schema={},
                engagement_name=self.engagement_name,
                run_id=self.run_id,
            )
            eval_result = evaluator.evaluate(
                input_data={
                    "code_string": input_data["code"],
                    "metadata": "empty",
                    "conversation": [],
                    "quality_aspect": "",
                },
                config={
                    "happy_cases_count": 0,
                    "edge_cases_count": self.config["number_of_edge_tests_to_generate"],
                },
                format_to_issues_scores=True,
            )
            eval_result["result"]["issues"] = "\n".join(eval_result["result"]["issues"])
        else:
            eval_result = super().evaluate(
                input_data,
                config,
                input_validation,
                parse,
                format_to_issues_scores=False,
            )
        issues = [{"turn": 1, "issues": [eval_result["result"]["issues"]]}]
        if issues[0]["issues"] and (
            "no_issues" in issues[0]["issues"][0].lower()
            or "no issues" in issues[0]["issues"][0][:20].lower()
        ):
            issues = []
        eval_result["result"] = {
            "issues": issues,
            "whole_conversation": False,
            "score": eval_result["result"]["score"],
        }
        return eval_result
