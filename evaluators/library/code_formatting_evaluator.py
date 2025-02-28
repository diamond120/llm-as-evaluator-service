import json
import os
import re
import time
import requests
from typing import Dict, Any, List, Tuple
from evaluators.langchain_evaluator_base import LangChainBaseEvaluator
from app.logging_config import logger


def get_nested_value(data: Dict[str, Any], path: str) -> str:
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


class CodeFormatEvaluator(LangChainBaseEvaluator):
    def _extract_code_blocks(self, content: str) -> List[Tuple[str, str, int, int]]:
        """
        Extract code blocks from content with their language and positions.
        Returns list of (language, code, start_pos, end_pos)
        Supports python, javascript/js, and go code blocks.
        """
        blocks = []
        pattern = r"```(python|javascript|js|go)?[\s\n]*(.*?)```"

        for match in re.finditer(pattern, content, re.DOTALL):
            lang = match.group(1)
            if lang:
                lang = lang.lower()
                if lang in ["javascript", "js"]:
                    lang = "js"
            else:
                lang = "python"

            code = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()

            logger.debug(
                f"Found code block - Language: {lang}, Length: {len(code)} chars, "
                f"Position: {start_pos}:{end_pos}, run_id: {self.run_id}"
            )
            blocks.append((lang, code, start_pos, end_pos))

        return blocks

    def _call_format_service(
        self, code: str, language: str, formatters: Dict[str, bool], options: str = None
    ) -> Dict[str, Any]:
        """Call the formatting service for code"""
        payload = {
            "code": f"```{language}\n{code}\n```",
            "language": language,
            "formatters": formatters,
            "options": options,
        }
        headers = {"Content-Type": "application/json"}
        formatter_url = f"{os.getenv('FORMATTER_URL', 'https://formatter.llm-as-evaluator.xxxx.com')}/formatCode/cvS0yn9lbI9Cnwrae7gM"

        start_time = time.time()
        try:
            response = requests.post(formatter_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            raise RuntimeError(
                f"Error calling format service: {str(e)}, run_id: {self.run_id}"
            ) from e
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.info(
                f"Format service call took {duration:.2f} seconds, run_id: {self.run_id}"
            )

        return result

    def evaluate(
        self, input_data: Dict[str, Any], config: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        try:
            # Parse guidelines
            guidelines = json.loads(config.get("quality_guidelines", "{}").strip())
            code_field = guidelines.get("code_field", "last_ai_reply.content")

            # Get formatter flags
            formatters = {
                "black": guidelines.get("black", False),
                "isort": guidelines.get("isort", False),
                "flake8": guidelines.get("flake8", False),
            }
            options = guidelines.get("options", "")

            # Get content
            content = get_nested_value(input_data, code_field)
            if not content:
                return {
                    "result": {
                        "formatted_code": [],
                        "explanation_for_the_evaluation_result": [],
                    }
                }

            # Extract all code blocks
            code_blocks = self._extract_code_blocks(content)
            if not code_blocks:
                return {
                    "result": {
                        "formatted_code": [],
                        "explanation_for_the_evaluation_result": [],
                    }
                }

            # Process each block separately
            formatted_blocks = []
            explanations = []

            for lang, code, _, _ in code_blocks:
                try:
                    # Call format service for each block
                    result = self._call_format_service(
                        code=code, language=lang, formatters=formatters, options=options
                    )

                    # Extract formatted code and changes
                    if result.get("success", False):
                        formatted_blocks.append(result.get("formatted_code", code))
                        if "changes" in result:
                            explanations.append(result["changes"])
                    else:
                        # If formatting failed, keep original code
                        formatted_blocks.append(f"```{lang}\n{code}\n```")
                        explanations.append(
                            result.get("changes", ["Formatting failed"])
                        )

                except Exception as e:
                    logger.error(
                        f"Error formatting code block: {str(e)}, run_id: {self.run_id}"
                    )
                    formatted_blocks.append(f"```{lang}\n{code}\n```")
                    explanations.append([f"Error: {str(e)}"])

            return {
                "result": {
                    "formatted_code": formatted_blocks,
                    "explanation_for_the_evaluation_result": explanations,
                }
            }

        except Exception as e:
            logger.error(f"Error in format evaluation: {str(e)}, run_id: {self.run_id}")
            raise RuntimeError(f"Formatting error: {str(e)}")

    def create_prompt(self, input_data: Dict[str, Any]):
        pass
