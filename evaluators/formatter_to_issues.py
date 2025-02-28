from typing import Any, List
from venv import logger

from langchain.output_parsers import PydanticOutputParser
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, validator
from llm_failover import ChatFailoverLLM
from tenacity import stop_after_attempt

from app.logging_config import logger


class Output(BaseModel):
    issues: list[str] = Field(
        ..., description="List of all gathered issues without loss of detail"
    )
    praises: list[str] = Field(
        ..., description="List of all gathered praises without loss of detail"
    )
    score: int = Field(..., ge=1, le=5, description="A score of the total evaluation")


SYSTEM_PROMPT = """
<|INPUT_DATA_START|>
```
{data}
```
<|INPUT_DATA_END|>

find all issues and convert them into a list of strings. Do not modify the words and style in issues, do not leave out fields and details. if a single issue is a structure, flatten it into a single string.

Example:

[{{"where": "in this piece of text", "what": "Problem with this word", "fix": "replace this word with another word", "severity": "critical"}},...] => ["Where: in this piece of text @|@ what: Problem with this word @|@ fix: replace this word with another word @|@ secerity: critical",...]

Find a single total score and extract it.
If a single Issue consists out of multiple key/values, combine them into "k: v @|@ k: v @|@ ".
You might reorder the keys inside each issues(consistent across all) if you think it improves readability and logical progression.

Output format:

{{"issues": ["issue1", "issue2", ...], "praises": ["praise1", "or not praises at all then empty list, but required list"], "score": int between 1 and 5}}

FINAL SCORE MUST BE GREATER THAN ZERO AND LESS THAN OR EQUAL TO 5. If you are provided with a different score, move it to the closest proper boundary: 0->1 and 10->5.
"""


def item_ok_for_manual_formatting(d):
    return isinstance(d, dict) and d.get("issues") is not None


def manual_dict_formatting(input_data):
    issues = input_data["issues"]
    score = input_data.get("score")
    formatted_issues = []
    for issue in issues:
        if isinstance(issue, dict):
            logger.debug("Formatting issue dictionary: %s", issue)
            formatted_issue = " @|@ ".join([f"{k}: {v}" for k, v in issue.items()])
            formatted_issues.append(formatted_issue)
        else:
            logger.debug("Appending issue: %s", issue)
            formatted_issues.append(issue)
        if len(formatted_issues) > 0 and isinstance(formatted_issues[-1], str):
            formatted_issues[-1] += "\n\n"
    return formatted_issues, score


def format_output_to_issues(input_data: Any, **kwargs) -> dict:
    """Format the input data and return the output as a dictionary."""
    run_id = kwargs.get("run_id", "unknown")
    logger.info("Starting format_output_to_issues function, run_id: %s", run_id)
    r = {}
    print("*" * 300)
    print(input_data)

    try:
        if item_ok_for_manual_formatting(input_data):
            logger.debug(
                "Input data is a dictionary with 'issues' and 'score', manually formatting it, run_id: %s",
                run_id,
            )
            formatted_issues, score = manual_dict_formatting(input_data)
            r["issues"] = formatted_issues
            r["score"] = score
        elif (
            isinstance(input_data, dict)
            and isinstance(input_data.get("multi_outputs", None), list)
            and (
                (
                    input_data["multi_outputs"]
                    and item_ok_for_manual_formatting(input_data["multi_outputs"][0])
                )
                or not input_data["multi_outputs"]
            )
        ):
            formatted_issues_list = []
            total_score = 0
            with_scores = 0
            for item in input_data["multi_outputs"]:
                if item_ok_for_manual_formatting(item):
                    formatted_issues, score = manual_dict_formatting(item)
                    formatted_issues_list.extend(formatted_issues)
                    total_score += score if score else 0
                    with_scores += bool(score)
            r["issues"] = formatted_issues_list
            r["score"] = total_score / max(with_scores, 1)
            if "stage2_output" in input_data:
                r.update(input_data["stage2_output"])
        elif (
            isinstance(input_data, dict)
            and isinstance(input_data.get("multi_outputs", None), list)
            and (
                (
                    input_data["multi_outputs"]
                    and isinstance(input_data["multi_outputs"][0], dict)
                    and "text" in input_data["multi_outputs"][0]
                )
                or not input_data["multi_outputs"]
            )
        ):
            r["issues"] = [
                item["text"] for item in input_data["multi_outputs"] if "text" in item
            ]
            r["score"] = 5
            if "stage2_output" in input_data:
                r.update(input_data["stage2_output"])
        else:
            logger.debug(
                "Input data is not a dictionary with 'issues' and 'score', using LLM to format, run_id: %s",
                run_id,
            )
            parser = PydanticOutputParser(pydantic_object=Output)
            prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT)])
            model = ChatFailoverLLM(initial_provider="openai_api", initial_model="gpt-4o-mini", temperature=0, seed=42)
            chain = (prompt | model | parser).with_retry(stop_after_attempt=2)

            logger.debug("Input data: %s, run_id: %s", input_data, run_id)
            r = chain.invoke({"data": input_data}).dict()

            logger.debug("Raw issues: %s, run_id: %s", r["issues"], run_id)
        r["issues"] = [
            issue.replace(" @|@ ", "\n\n").replace("@|@", "\n\n") + "\n\n"
            for issue in r.get("issues", [])
            if isinstance(issue,str)
        ]
    except Exception as e:
        logger.error(
            "An error occurred in format_output_to_issues, run_id: %s",
            run_id,
            exc_info=e,
        )
        raise
    logger.debug("Formatted issues: %s, run_id: %s", r["issues"], run_id)
    logger.info("Completed format_output_to_issues function, run_id: %s", run_id)
    return r
