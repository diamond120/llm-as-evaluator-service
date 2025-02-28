from pydantic import BaseModel, Field
from typing import Dict, Any, List

from app.logging_config import logger
from evaluators.library.single_stage_system_prompt import (
    SingleStageSystemPromptEvaluator,
)


class MainInputSchema(BaseModel):
    conversation: list[dict] = Field(
        ...,
        description="List of cells with Assistant cells containing multiple model responses and human feedback.",
    )


class SingleEvalInputSchema(BaseModel):
    conversation: list[dict] = Field(
        ...,
        description="History before the cell being evaluated",
    )
    model_responses: list
    responses_feedbacks: list
    chosen_model_id: str
    chosen_model_response: str
    optionally_suggested_response: str


def reconstruct_conversation_history_for_index(conversation, idx):
    logger.debug(f"Reconstructing conversation history up to index {idx}")
    reconstructed_conversation = []
    for i in range(idx):
        cell = conversation[i]
        if cell["role"] == "user":
            reconstructed_conversation.append(
                {"role": cell["role"], "content": cell["content"]}
            )
        else:
            content = next(
                item["content"]
                for item in cell["response_options"]
                if item["model_id"] == cell["selected_response_model_id"]
            )
            reconstructed_conversation.append(
                {"role": cell["role"], "content": content}
            )
    logger.debug(f"Reconstructed conversation history: {reconstructed_conversation}")
    return reconstructed_conversation


def extract_detailed_assistant_data(assistant_cell):
    """
    Extracts detailed fields from an assistant cell in the conversation.
    """
    logger.debug("Extracting detailed assistant data")
    model_responses = assistant_cell["response_options"]
    responses_feedbacks = assistant_cell["human_eval"]
    chosen_model_id = assistant_cell["selected_response_model_id"]
    chosen_model_response = next(
        (
            item["content"]
            for item in model_responses
            if item["model_id"] == chosen_model_id
        ),
        None,
    )
    optionally_suggested_response = assistant_cell["human_ideal_response"]

    extracted_data = {
        "model_responses": model_responses,
        "responses_feedbacks": responses_feedbacks,
        "chosen_model_id": chosen_model_id,
        "chosen_model_response": chosen_model_response,
        "optionally_suggested_response": optionally_suggested_response,
    }
    logger.debug(f"Extracted data: {extracted_data}")
    return extracted_data


class RLHFEvaluator(SingleStageSystemPromptEvaluator):

    def evaluate(
        self,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        input_validation: bool = True,
        parse: bool = True,
    ) -> Dict[str, Any]:

        logger.info("Starting evaluation")
        input_data = {**input_data, **config}
        self.validate_input(input_data)
        logger.debug("Input data validated")

        sub_evaluator = SingleStageSystemPromptEvaluator(
            "sub_" + self.name,
            {"system_prompt": self.config["single_response_system_prompt"]},
            self.llm_config,
            SingleStageSystemPromptEvaluator.ConfigSchema.model_json_schema(),
            SingleEvalInputSchema.model_json_schema(),
            self.output_schema,
        )
        results = []
        total_metadata = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        for idx, cell in enumerate(input_data["conversation"]):
            if cell["role"] == "user":
                continue
            logger.debug(f"Evaluating assistant cell at index {idx}")
            extracted_data = extract_detailed_assistant_data(
                input_data["conversation"][idx]
            )
            cell_result = sub_evaluator.evaluate(
                {
                    "conversation": reconstruct_conversation_history_for_index(
                        input_data["conversation"], idx
                    ),
                    **extracted_data,
                },
                config,
                parse=parse,
            )

            # Extract and aggregate token usage
            cell_metadata = cell_result.get("metadata", {})
            for key in total_metadata:
                total_metadata[key] += cell_metadata.get(key, 0)

            results.append(cell_result.get("result", {}))
            logger.debug(f"Result for index {idx}: {cell_result.get('result', {})}")

        logger.info("Evaluation completed")
        return {"metadata": total_metadata, "result": results}
