import copy
import os
from abc import ABC, abstractmethod

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from app.logging_config import logger
from common.exceptions import ValidationException
from common.utils import load_env, num_tokens_from_string


def restore_order(schema_dict):
    schema_dict = copy.deepcopy(schema_dict)

    def reorder_dict(d, order):
        return {k: d[k] for k in order if k in d}

    def process_properties(properties, required):
        for prop in required:
            if prop in properties:
                properties[prop] = restore_order(properties[prop])
        return reorder_dict(properties, required) | {
            k: v for k, v in properties.items() if k not in required
        }

    if not isinstance(schema_dict, dict):
        return schema_dict

    # Restore the main schema order
    main_order = [
        "title",
        "description",
        "type",
        "required",
        "properties",
        "definitions",
        "$defs",
    ]
    schema_dict = reorder_dict(schema_dict, main_order) | {
        k: v for k, v in schema_dict.items() if k not in main_order
    }

    # Process properties
    if "properties" in schema_dict and "required" in schema_dict:
        schema_dict["properties"] = process_properties(
            schema_dict["properties"], schema_dict["required"]
        )

    # Process definitions recursively
    if "definitions" in schema_dict:
        for key, value in schema_dict["definitions"].items():
            schema_dict["definitions"][key] = restore_order(value)

    return schema_dict


class BaseEvaluator(ABC):
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
        self.name = name
        self.engagement_name = engagement_name
        self.run_id = run_id
        self.config_schema = config_schema
        self.config = config
        self.input_schema = input_schema
        logger.debug("Before order output schema fix", extra=output_schema)

        self.output_schema = (
            restore_order(output_schema) if output_schema else output_schema
        )
        logger.debug("After order output schema fix", extra=self.output_schema)
        self.llm_config = llm_config
        logger.debug(f"Initializing BaseEvaluator with name: {name}")
        if config_validation:
            self.validate_schema(config_schema, config)
        if self.output_schema and "description" not in self.output_schema:
            logger.error("Output schema must have a top-level description.")
            raise ValueError("Output schema must have a top-level description.")

    def validate_schema(self, schema, data):
        logger.debug("Validating schema")
        logger.debug(f"Schema: {schema}")
        logger.debug(f"Data: {data}")
        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            error_message = f"Validation error: {e.message}"
            logger.exception(error_message)
            raise ValidationException(error_message)

    @abstractmethod
    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False,
    ):
        pass
    

    def validate_input(self, input_data, **kwargs):
        logger.debug("Validating input data")
        self.validate_schema(self.input_schema, input_data)
        # Commenting out while fixing apple issue
        #self.count_tokens_and_validate(input_data)

    def count_tokens_and_validate(self, input_data):
        logger.debug("Counting tokens and validating input data")
        env_vars = load_env()
        max_tokens = int(env_vars.get("MAX_TOKENS_IN_PROMPT", 10000))
        token_count = num_tokens_from_string(input_data)
        logger.debug(f"Token count: {token_count}, Max tokens allowed: {max_tokens}")
        if token_count > max_tokens:
            logger.error(
                f"Input data exceeds the maximum allowed tokens of {max_tokens}. Found {token_count} tokens."
            )
            raise ValueError(
                f"Input data exceeds the maximum allowed tokens of {max_tokens}. Found {token_count} tokens."
            )
