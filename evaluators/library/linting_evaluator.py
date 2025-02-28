from dataclasses import dataclass
import os
import re
import time
import requests
from typing import Dict, Any, List, Optional, Tuple, Union
from evaluators.langchain_evaluator_base import LangChainBaseEvaluator
from app.logging_config import logger


def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get value from nested dictionary using dot notation.
    Example: get_nested_value(data, "last_ai_reply.content")
    """
    try:
        for key in path.split("."):
            data = data.get(key, {})
        return data if not isinstance(data, dict) or data else ""
    except (AttributeError, TypeError):
        return ""


@dataclass
class LintingIssue:
    """Standardized structure for linting issues across languages"""

    line: int
    column: int
    message: str
    issue_type: str
    category: Optional[str] = None


class LintingEvaluator(LangChainBaseEvaluator):
    def _extract_code_blocks(self, content: str) -> List[Tuple[str, str, int, int]]:
        """
        Extract code blocks from content with their language and positions.
        Returns list of (language, code, start_pos, end_pos)
        Supports python, javascript/js, and go code blocks.

        Returns:
            List[Tuple[str, str, int, int]]: List of tuples containing:
                - language: Detected programming language
                - code: The code content
                - start_pos: Start position of the block
                - end_pos: End position of the block
        """
        blocks = []
        # Pattern to match code blocks with language specification
        pattern = r"```(python|javascript|js|go)?[\s\n]*(.*?)```"

        for match in re.finditer(pattern, content, re.DOTALL):
            # Get language, defaulting to python if not specified
            lang = match.group(1)
            if lang:
                lang = lang.lower()
                # Normalize language names
                if lang in ["javascript", "js"]:
                    lang = "js"
            else:
                lang = "python"  # Default to python if no language specified

            code = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()

            logger.debug(
                f"Found code block - Language: {lang}, Length: {len(code)} chars, "
                f"Position: {start_pos}:{end_pos}, run_id: {self.run_id}"
            )

            blocks.append((lang, code, start_pos, end_pos))

        return blocks

    def evaluate(
        self, input_data: Dict[str, Any], config: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        logger.debug(
            "Lint Evaluating input data: %s with config: %s, run_id: %s",
            input_data,
            config,
            self.run_id,
        )
        # Parse quality guidelines
        try:
            guidelines = eval(config.get("quality_guidelines", "{}"))
            logger.debug(
                "Parsed quality guidelines: %s, run_id: %s", guidelines, self.run_id
            )
        except Exception as e:
            logger.error(
                "Error parsing quality guidelines: %s, run_id: %s", str(e), self.run_id
            )
            guidelines = {}

        # Extract code field path, language, and options from guidelines
        code_field_path = guidelines.get("code_field", "last_ai_reply.content")
        configured_language = guidelines.get("language", "")
        options = guidelines.get("options", "")

        # Get code content using the specified field path
        code_content = get_nested_value(input_data, code_field_path)

        # Extract all code blocks
        code_blocks = self._extract_code_blocks(code_content)
        if not code_blocks:
            logger.debug(
                "No code blocks found, returning pass, run_id: %s", self.run_id
            )
            return {
                "result": {
                    "evaluation_result": "PASS",
                    "explanation_for_the_evaluation_result": "No code blocks found",
                }
            }

        # Combine all code blocks with proper separation
        combined_code = []
        for i, (lang, code, _, _) in enumerate(code_blocks):
            combined_code.extend(
                [f"# Code Block {i}", code, ""]  # Empty line between blocks
            )

        combined_code_str = "\n".join(combined_code)
        language = lang

        logger.debug(
            "Combined code blocks: %s, run_id: %s", combined_code_str, self.run_id
        )

        if not combined_code_str:
            logger.debug("No code found, returning pass, run_id: %s", self.run_id)
            return {
                "result": {
                    "evaluation_result": "PASS",
                    "explanation_for_the_evaluation_result": "No code found",
                }
            }

        logger.debug(
            "Extracted language: %s, Extracted code: %s, run_id: %s",
            language,
            combined_code_str,
            self.run_id,
        )
        response = self._call_linting_service(combined_code_str, language, options)

        evaluation_result = self._parse_linting_response(response, language)
        logger.debug(
            "Linting evaluation result: %s, run_id: %s", evaluation_result, self.run_id
        )

        return {"result": evaluation_result}

    def _call_linting_service(
        self,
        code: str,
        language: str,
        options: str,
    ) -> Union[Dict[str, Any], float]:
        """
        Call the linting service with the provided code and options.

        This function sends a POST request to a linting service with the given code,
        language, and options. It measures the time taken for the request and logs it.

        Args:
            code (str): The code to be linted.
            language (str): The programming language of the code.
            options (str): Additional options for the linting service.

        Returns:
            Union[Dict[str, Any], float]: The JSON response from the linting service,
            which is expected to be a dictionary or a float.

        Raises:
            ValueError: If the LINTER_URL environment variable is not set.
            RuntimeError: If there's an error in calling the linting service.
        """
        payload = {"code": code, "language": language, "options": options or ""}
        headers = {"Content-Type": "application/json"}
        linter_url = os.getenv("LINTER_URL")

        if not linter_url:
            raise ValueError("LINTER_URL environment variable not set")

        start_time = time.time()
        try:
            response = requests.post(linter_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            raise RuntimeError(
                f"Error calling linting service: {str(e)}, run_id: {self.run_id}"
            ) from e
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.info(
                f"Linting service call took {duration:.2f} seconds, run_id: {self.run_id}"
            )

        return result

    def _parse_go_issue(self, issue: Dict[str, Any]) -> LintingIssue:
        """Parse Go-specific linting issue"""
        pos = issue.get("Pos", {})
        return LintingIssue(
            line=pos.get("Line", 0),
            column=pos.get("Column", 0),
            message=issue.get("Text", ""),
            issue_type="warning",
            category=issue.get("Category", "style"),
        )

    def _parse_python_issue(self, issue: Dict[str, Any]) -> LintingIssue:
        """Parse Python-specific linting issue"""
        return LintingIssue(
            line=issue.get("line", 0),
            column=issue.get("column", 0),
            message=issue.get("message", ""),
            issue_type=issue.get("type", "unknown"),
            category=issue.get("message-id", ""),
        )

    def _parse_js_result(
        self, result: Union[str, Dict[str, Any], List[Dict[str, Any]]]
    ) -> Union[str, List[LintingIssue]]:
        """
        Parse JavaScript linting results
        Returns either a string for simple messages or list of LintingIssue for structured results
        """
        if isinstance(result, str):
            return result

        if isinstance(result, dict) and "messages" in result:
            issues = []
            for msg in result["messages"]:
                issues.append(
                    LintingIssue(
                        line=msg.get("line", 0),
                        column=msg.get("column", 0),
                        message=msg.get("message", ""),
                        issue_type=msg.get("severity", "error"),
                        category=msg.get("ruleId", ""),
                    )
                )
            return issues

        if isinstance(result, list):
            issues = []
            for msg in result:
                if isinstance(msg, str):
                    return msg
                issues.append(
                    LintingIssue(
                        line=msg.get("line", 0),
                        column=msg.get("column", 0),
                        message=msg.get("message", ""),
                        issue_type=msg.get("severity", "error"),
                        category=msg.get("ruleId", ""),
                    )
                )
            return issues

        return str(result)

    def format_linter_output(
        self, issues: Union[str, List[LintingIssue]], language: str
    ) -> str:
        """Format linting results based on language and issue type"""
        header = f"## {language.title()} Linting Results\n"

        # Handle JavaScript string output
        if language.lower() == "javascript" and isinstance(issues, str):
            return f"{header}{issues}"

        # Handle structured issues
        if not issues:
            return f"{header}No issues found."

        if isinstance(issues, list):
            formatted_issues = []
            for issue in issues:
                formatted_issue = (
                    f"** Line {issue.line}, Column {issue.column}: "
                    f"{issue.issue_type.title()} - {issue.message}"
                )
                if issue.category:
                    formatted_issue += f" ({issue.category})"
                formatted_issues.append(formatted_issue)
            return header + "<br/>".join(formatted_issues)

        return f"{header}{str(issues)}"

    def _parse_linting_response(
        self,
        linting_result: Union[Dict[str, Any], List[Union[Dict[str, Any], str]], str],
        language: str,
    ) -> Dict[str, Any]:
        """Parse linting results based on language"""
        try:
            language = language.lower()

            if language == "js":
                issues = self._parse_js_result(linting_result)

            elif language == "go":
                if isinstance(linting_result, dict):
                    issues = [
                        self._parse_go_issue(issue)
                        for issue in linting_result.get("Issues", [])
                        if isinstance(issue, dict)
                    ]
                else:
                    issues = []

            elif language == "python":
                if isinstance(linting_result, list):
                    issues = [
                        self._parse_python_issue(issue)
                        for issue in linting_result
                        if isinstance(issue, dict)
                        and issue.get("message-id") != "F0001"
                    ]
                else:
                    issues = []

            # Generate formatted output
            formatted_output = self.format_linter_output(issues, language)

            # For JavaScript string output or non-empty issue lists
            has_issues = isinstance(issues, str) or (
                isinstance(issues, list) and issues
            )

            return {
                "evaluation_result": "PASS" if not has_issues else "FAIL",
                "explanation_for_the_evaluation_result": formatted_output,
            }

        except Exception as e:
            error_msg = f"Error parsing {language} linting results: {str(e)}"
            logger.error(f"{error_msg}, run_id: {self.run_id}")
            return {
                "evaluation_result": "ERROR",
                "explanation_for_the_evaluation_result": error_msg,
            }

    def create_prompt(self, input_data: Dict[str, Any]):
        pass
