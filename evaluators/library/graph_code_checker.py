import json
from typing import Any, List, Optional

from pydantic import BaseModel, Field

import agents
from app.logging_config import logger
from common.exceptions import ValidationException
from evaluators.evaluator_base import BaseEvaluator


class InputSchema(BaseModel):
    """
    This class represents the input schema for the graph code checker.
    It includes metadata, conversation data, and counts for happy and edge cases.
    """

    metadata: Optional[Any] = Field(
        ..., description="The metadata of the input. Used when mode is 'conversation'."
    )
    conversation: Optional[List[dict]] = Field(
        None, description="The conversation data. Used when mode is 'conversation'."
    )
    text_with_code: Optional[str] = Field(
        None,
        description="Text that includes code snippets. Used when mode is 'text_with_code'.",
    )
    code_string: Optional[str] = Field(
        None, description="A string containing code. Used when mode is 'code_string'."
    )
    happy_cases_count: Optional[int] = Field(3, description="The number of happy cases")
    edge_cases_count: Optional[int] = Field(5, description="The number of edge cases")


class OutputSchema(BaseModel):
    """
    This class represents the output schema for the graph code checker.
    It includes a list of issues and an average score for all turns.
    """

    issues: List[str] = Field(..., description="List of issues in string format.")
    score: float = Field(..., description="Average score of all turns.")


class ConfigSchema(BaseModel):
    """
    This class represents the configuration schema for the graph code checker.
    It includes settings for recursion limits and worker counts.
    """

    graph_recursion: int = Field(
        default=30, description="Recursion limit for graph processing."
    )
    turn_workers: int = Field(
        default=4, description="Number of workers for processing turns."
    )
    test_workers: int = Field(
        default=4, description="Number of test runners per turn in parallel."
    )
    mode: str = Field(
        default="conversation",
        description="One of conversation, text_with_code, code_string",
    )
    run_code: bool = Field(default=True, description="Whether to execute the code.")
    agent_dependencies_extraction: bool = Field(
        default=False, description="Whether to extract package dependencies."
    )
    turn_grouping: bool = Field(
        default=True, description="Whether to group turns during processing."
    )


class GraphCodeCheckerEvaluator(BaseEvaluator):
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

    def format_output_to_issues(self, in_):
        logger.debug("FORMATTER IN: " + str(in_))
        issues = []
        total_score = 0
        second_branch_involved = False

        for i, turn in enumerate(in_):
            eval_ = turn.get("eval", {})
            issues.append(f"# Turn: {i}\n\n")
            if "issues" in eval_:
                for issue in eval_.get("issues", []):
                    issue_str = f"**What:** {issue.get('what', '')}\n\n"
                    issue_str += f"**Why:** {issue.get('why', '')}\n\n"
                    issue_str += f"**Where:** {issue.get('where', '')}\n\n"
                    issue_str += f"**Severity:** {issue.get('severity', '')}\n\n"
                    issue_str += f"**Fix:** {issue.get('fix', '')}\n\n"
                    issue_str += "\n\n"
                    issues.append(issue_str)
                total_score += eval_.get("score", 0)
            else:
                second_branch_involved = True
                issue_str = (
                    f"# Turn: {i}\n\n"
                    f"**Has Code:** {turn.get('has_code', False)}\n\n"
                    f"**Complete Code:** {turn.get('complete_code', False)}\n\n"
                    f"**Can Be Tested:** {turn.get('can_be_tested', False)}\n\n"
                    f"**Reason It Can't Be Tested:** {turn.get('reason_it_cant_be_tested', '')}\n\n"
                    f"**Code:** {turn.get('code', '')}\n\n"
                    f"**Dependencies:** {turn.get('dependencies', [])}\n\n"
                    f"**Language:** {turn.get('language', '')}\n\n"
                )
                results = turn.get("results", [])
                for result in results:
                    issue_str += f"**Results Comment:** {result.get('comment', '')}\n"
                    test_exec = (
                        result.get("test_execution", {})
                        .get("CodeExec", {})
                        .get("run", {})
                    )
                    issue_str += f"**Results Error:** {test_exec.get('error', '')}\n"
                issue_str += "\n\n"
                issues.append(issue_str)
                total_score += 1  # Set score to 1 for this turn

            # Gather test details for each turn
            if turn.get("can_be_tested", False):
                test_detail = f"**Extracted code:**\n```{turn.get('language', 'code')}\n{turn.get('code', '')}\n```\n"
                test_detail += "**Test Results:**\n"
                for ii, (test_idea, result) in enumerate(
                    zip(turn.get("tests", []), turn.get("results", []))
                ):
                    test_detail += f"## Test Idea {ii+1}: {test_idea}\n\n"
                    test_detail += f"**Test Result:** {result.get('result', '')}\n\n"
                    test_detail += f"**Test Comment:** {result.get('comment', '')}\n\n"
                    test_detail += f"**Test code:**\n```{turn.get('language', 'code')}\n\n{result.get('test_code', '')}\n```\n"
                    test_exec = result.get("test_execution", {})
                    if not test_exec:
                        test_exec = {}
                    test_exec = test_exec.get("ExecuteCodeTool", {})
                    test_detail += "#### Test Output:\n"
                    if "run" in test_exec:
                        test_exec = test_exec["run"]
                    test_detail += f"```json\n{json.dumps(test_exec, indent=4)}\n```\n"
                issues.append("\n\n\n# Extra\n")
                issues.append(test_detail)

        final_score = (
            1 if second_branch_involved else (total_score / len(in_) if in_ else 0)
        )
        return {
            "issues": issues,
            "score": final_score if final_score != 0 else 5,
        }

    def get_config_values(self):
        return {
            "recursion_limit": self.config.get(
                "graph_recursion", ConfigSchema.model_fields["graph_recursion"].default
            ),
            "n_workers": self.config.get(
                "turn_workers", ConfigSchema.model_fields["turn_workers"].default
            ),
            "n_workers_inner_thread": self.config.get(
                "test_workers", ConfigSchema.model_fields["test_workers"].default
            ),
            "mode": self.config.get("mode", ConfigSchema.model_fields["mode"].default),
            "run_code": self.config.get(
                "run_code", ConfigSchema.model_fields["run_code"].default
            ),
            "agent_dependencies_extraction": self.config.get(
                "agent_dependencies_extraction",
                ConfigSchema.model_fields["agent_dependencies_extraction"].default,
            ),
            "turn_grouping": self.config.get(
                "turn_grouping", ConfigSchema.model_fields["turn_grouping"].default
            ),
        }

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

        # Ensure consistency between mode and input values
        config_values = self.get_config_values()
        mode = config_values["mode"]
        if mode == "conversation" and input_data.get("conversation", "@@@") == "@@@":
            raise ValidationException(
                "Mode is 'conversation' but 'conversation' data is missing."
            )
        elif (
            mode == "text_with_code"
            and input_data.get("text_with_code", "@@@") == "@@@"
        ):
            raise ValidationException(
                "Mode is 'text_with_code' but 'text_with_code' data is missing."
            )
        elif mode == "code_string" and input_data.get("code_string", "@@@") == "@@@":
            raise ValidationException(
                "Mode is 'code' but 'code_string' data is missing."
            )
        elif mode not in ["conversation", "text_with_code", "code_string"]:
            raise Exception(
                f"Unknown mode specified in the configuration {mode} or data is missing, {input_data.keys()=}."
            )

        logger.info("Running multiple turns...")

        happy_cases_n = config.get(
            "happy_cases_count",
            InputSchema.model_fields["happy_cases_count"].default,
        )
        edge_cases_n = config.get(
            "edge_cases_count",
            InputSchema.model_fields["edge_cases_count"].default,
        )
        expanded_config = {
            "recursion_limit": config_values.get("recursion_limit", 40),
            "n_workers": config_values.get("n_workers", 4),
            "n_workers_inner_thread": config_values.get("n_workers_inner_thread", 4),
            "run_code": config_values.get("run_code", True),
            "agent_dependencies_extraction": config_values.get(
                "agent_dependencies_extraction", False
            ),
            "turn_grouping": config_values.get("turn_grouping", True),
            "provider": config_values.get("provider", "openai_api"),
            "try_and_fix_output": config_values.get("try_and_fix_output", True),
        }
        expanded_config2 = {
            "recursion_limit": config_values.get("recursion_limit", 30),
            "n_workers_inner_thread": config_values.get("n_workers_inner_thread", 4),
            "run_code": config_values.get("run_code", True),
            "provider": config_values.get("provider", "openai_api"),
            "try_and_fix_output": config_values.get("try_and_fix_output", True),
        }
        if config_values["mode"] == "conversation":
            graph_out = agents.run_multiple_turns(
                notebook_path=None,
                loaded_notebook=input_data,
                happy_cases_n=happy_cases_n,
                edge_cases_n=edge_cases_n,
                **expanded_config,
                use_gevent=True,
            )
        elif config_values["mode"] == "text_with_code":
            text_with_code = input_data.get("text_with_code")

            graph_out = agents.run_code_text(
                code=text_with_code,
                happy_cases_n=happy_cases_n,
                edge_cases_n=edge_cases_n,
                **expanded_config2,
                use_gevent=True,
            )
            graph_out = [graph_out]
        elif config_values["mode"] == "code_string":
            code_string = input_data.get("code_string")
            graph_out = agents.run_code_text(
                code=code_string,
                happy_cases_n=happy_cases_n,
                edge_cases_n=edge_cases_n,
                **expanded_config2,
                use_gevent=True,
            )
            graph_out = [graph_out]

        logger.info("Formatting output...")
        if format_to_issues_scores:
            return {"result": self.format_output_to_issues(graph_out)}
        else:
            return {"result": graph_out}
