from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from evaluators.graph_llm_modules.state_graph import get_runnable_graph
from app.logging_config import logger
from evaluators.evaluator_base import BaseEvaluator


class GraphLLMInputSchema(BaseModel):
    conversation_metadata: Optional[Any] = Field(..., description="The metadata of the input")
    user_prompt: Dict[str, str] = Field(..., description="User's input prompt")
    last_ai_reply: Dict[str, str] = Field(..., description="Last AI assistant reply")
    other_model_responses: Optional[List[Dict[str, str]]] = Field(
        default=[],
        description="Optional responses from other models"
    )


class GraphLLMOutputSchema(BaseModel):
    """Schema for Graph LLM evaluation output that includes filtered issues and meta review results."""

    filtered_issues: List[Dict[str, Any]] = Field(
        default=[],
        description="List of filtered issues found during evaluation"
    )
    meta_review_result: Dict[str, Any] = Field(
        default={},
        description="Meta review results"
    )
    evaluation_result: str = Field(..., description="Final evaluation result: PASS OR FAIL")
    explanation_for_the_evaluation_result: str = Field(..., description="Final explanation for evaluation result")



class GraphLLMEvaluator(BaseEvaluator):
    def evaluate(
        self,
        input_data,
        config,
        input_validation=True,
        parse=True,
        format_to_issues_scores=False
    ):
        logger.info("Starting evaluation...")

        try:
            if input_validation:
                logger.info("Validating input data...")
                self.validate_input({**input_data, **config})

            conversation_metadata_content = input_data.get("conversation_metadata", {})
            user_prompt_content = input_data.get("user_prompt", {}).get("content")
            last_ai_reply_content = input_data.get("last_ai_reply", {}).get("content")
            other_model_responses = input_data.get("other_model_responses", [])
            other_model_responses_content = other_model_responses[0].get("content") if other_model_responses else None

            if not user_prompt_content or not last_ai_reply_content:
                raise ValueError("Missing user prompt or last AI reply content")

            inputs = {
                "last_ai_reply": last_ai_reply_content,
                "user_prompt": user_prompt_content,
                "extra_latest_ai_reply": other_model_responses_content,
                "conversation_metadata": conversation_metadata_content,
                "meta_review_result": {},
                "filtered_issues": [],
                "results_for_meta_review": [],
            }

            graph = get_runnable_graph()
            result = graph.invoke(inputs)

            result["evaluation_result"] = "PASS" if len(result["filtered_issues"]) == 0 else \
            result["meta_review_result"]["result"]
            result["explanation_for_the_evaluation_result"] = self.issues_to_md(result["filtered_issues"])

            if parse:
                result = self._parse_result(result)

            return {"result": result}

        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            raise

    def _parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the graph output."""
        try:
            return GraphLLMOutputSchema(**result).model_dump()
        except Exception as e:
            logger.error(f"Failed to parse result: {str(e)}")
            raise ValueError(f"Invalid output format: {str(e)}")

    def issues_to_md(self, issues):
        m = ""
        # Sort issues by severity with custom order
        severity_order = {"Critical": 0, "Moderate": 1, "Minor": 2}
        sorted_issues = sorted(
            issues,
            key=lambda x: severity_order.get(x["severity"].lower().capitalize(), 999),
        )

        for i in sorted_issues:
            m += f"- Issue: {i['issue']}\n"
            m += f"- Fix: {i['fix']}\n\n"
        return m
