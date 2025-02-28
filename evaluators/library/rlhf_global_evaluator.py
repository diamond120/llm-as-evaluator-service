import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.logging_config import logger
from evaluators.library.single_stage_messages import SingleStageMessagesEvaluator


def get_value_from_path(current_data, segments):
    if not segments:
        return current_data

    segment = segments[0]

    # Handle conditions in the form of "key=value"
    if "=" in segment:
        key, value = segment.split("=")
        # Unescape any escaped dots in the key or value
        key = key.replace(r"\.", ".")
        value = value.replace(r"\.", ".")
        if isinstance(current_data, list):
            # Filter the list based on the condition (key=value)
            filtered_data = [
                item
                for item in current_data
                if isinstance(item, dict) and item.get(key) == value
            ]
            # Recursively apply the function to the filtered list
            return [get_value_from_path(item, segments[1:]) for item in filtered_data]
        elif isinstance(current_data, dict):
            current_data = current_data.get(key)
            return get_value_from_path(current_data, segments[1:])

    # Traverse lists and dicts
    if isinstance(current_data, list):
        # Apply the recursive function to each element in the list
        return [get_value_from_path(item, segments) for item in current_data]
    elif isinstance(current_data, dict):
        # Unescape any escaped dots in the segment
        segment = segment.replace(r"\.", ".")
        # Traverse the dictionary
        return get_value_from_path(current_data.get(segment), segments[1:])

    return None


def parse_payload(payload, extracted_input_fields_map):
    filtered_payload = {}

    # Process each extracted field and fetch the corresponding value from the payload
    for field in extracted_input_fields_map.keys():
        # Split the field path into segments, handling escaped dots
        path_segments = re.split(
            r"(?<!\\)\.", field
        )  # Split by dots, ignoring escaped dots
        # Recursively fetch the value from the payload based on the path
        value = get_value_from_path(payload, path_segments)
        filtered_payload[field] = value

    return filtered_payload


def parse_evaluation_rules(evaluation_rules: str):
    # Split the evaluation_rules into sections
    sections = re.split(r"@@@", evaluation_rules.strip())
    if len(sections) != 3:
        raise ValueError(
            "Invalid format. The evaluation rules must contain two '@@@' delimiters."
        )

    # Parse the input fields and corresponding instructions section
    field_instructions_lines = sections[1].strip().split("\n")
    extracted_input_fields_map = {}

    for line in field_instructions_lines:
        if "->" in line:
            field, instruction = map(str.strip, line.split("->"))
            extracted_input_fields_map[field] = instruction

    # The actual rules are in the last section
    actual_rules = sections[2].strip()

    return extracted_input_fields_map, actual_rules


def system_prompt_modification(messages, extracted_input_fields_map):
    # Find the system message
    system_message = None
    for i, message in enumerate(messages):
        if message[0] == "system":
            system_message = message[1]
            system_message_index = i
            break

    if system_message is None:
        raise ValueError("No system message found in the provided messages.")

    # Add dynamic instructions based on extracted input fields
    dynamic_instructions = "\n### Base your evaluation on these input fields:\n"

    for input_field, guidelines in extracted_input_fields_map.items():
        dynamic_instructions += f"- {input_field}: {guidelines}\n"

    # Update the system message with the dynamic instructions
    modified_system_message = (
        system_message
        + "<|INPUT FIELDS DESCRIPTION START|>\n\n"
        + dynamic_instructions
        + "<|INPUT FIELDS DESCRIPTION END|>\n\n"
    )

    # Add placeholder for the notebook conversation, to be inserted later
    placeholder_prompt = (
        "### Conversation\n<|CONVERSATION START|>\n{payload}<|CONVERSATION END|>\n\n"
    )

    # Add instructions for final score and rationale
    final_score_instructions = (
        "### Final Evaluation:\n"
        "- Analyze the conversation in the context of the quality and provided input fields.\n"
        "- Assign a score for the conversation based on your assessment (on a scale of 1 to 5, where 1 is poor and 5 is excellent).\n"
        "- Provide reasoning for why this score was assigned, focusing on key aspects of clarity, correctness, and the overall quality of the conversation in the .\n"
    )

    # Append placeholders and final score instructions to the system message
    modified_system_message += placeholder_prompt + final_score_instructions

    # Update the system message in the original list of messages
    messages[system_message_index] = ("system", modified_system_message)

    return messages


class RLHFGlobalEvaluator(SingleStageMessagesEvaluator):

    class RequiredInputSchema(BaseModel):
        """Schema for required input fields with descriptions"""

        evaluation_rules: str = Field(
            ..., description="Evaluation rules with field and description."
        )

    def create_prompt(self, input_data):
        logger.debug("Creating prompt with input data: %s", input_data)
        messages = self.config["messages"]
        messages = system_prompt_modification(
            messages, input_data["extracted_input_fields_map"]
        )
        logger.debug("Loaded messages from config: %s", messages)
        messages = [tuple(message) for message in messages]
        logger.debug("Converted messages to tuples: %s", messages)
        try:
            chat_template = ChatPromptTemplate.from_messages(messages)
            logger.info("Chat template created successfully")
        except Exception as e:
            logger.error("Failed to create chat template", exc_info=True)
            raise e
        return chat_template

    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=None,
        format_to_issues_scores=False,
    ):
        extracted_input_fields_map, quality_evaluation_rules = parse_evaluation_rules(
            config["quality_evaluation_rules"]
        )
        config["quality_evaluation_rules"] = quality_evaluation_rules
        input_data["payload"] = parse_payload(
            input_data["payload"], extracted_input_fields_map
        )
        config["extracted_input_fields_map"] = extracted_input_fields_map
        return super().evaluate(
            input_data,
            config,
            input_validation=input_validation,
            parse=parse,
            format_to_issues_scores=format_to_issues_scores,
        )
