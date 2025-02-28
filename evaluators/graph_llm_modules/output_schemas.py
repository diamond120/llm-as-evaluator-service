from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    issue: str = Field(..., description="DETAILED description of the quality issue")
    fix: str = Field(..., description="Suggested fix for the issue")
    severity: str = Field(
        ..., description="Severity level of the issue - Minor, Critical, Moderate"
    )


class PromptEvaluationResult(BaseModel):
    """Represents the result of evaluating both user prompt and assistant's handling of any issues."""

    chain_of_thought_process: str = Field(
        ..., 
        description="""Detailed reasoning process showing:
        1. Analysis of user prompt for potential issues
        2. [If issues found] Analysis of assistant's handling of these issues
        3. Final determination"""
    )
    list_of_quality_issues: list[QualityIssue] = Field(
        ..., 
        description="""List of identified user prompt issues that the assistant missed"""
    )
    result: str = Field(
        ..., 
        description="""Evaluation result:
        PASS - No issues in prompt OR issues properly handled by assistant
        FAIL - Issues found in prompt AND not properly handled by assistant"""
    )
    short_explanation: str = Field(
        ..., description="Brief explanation of the evaluation result"
    )


class EvaluationResult(BaseModel):
    """Represents the result of an evaluation process."""

    chain_of_thought_process: str = Field(
        ..., description="Detailed reasoning process used during evaluation"
    )
    place_to_reason: str = Field(
        ..., description="Location or reason for the evaluation"
    )

    list_of_quality_issues: list[QualityIssue] = Field(
        ..., description="List of identified quality issues"
    )
    result: str = Field(..., description="Evaluation result: PASS OR FAIL")
    short_explanation: str = Field(
        ..., description="Brief explanation of the evaluation result"
    )


class ComparativeEvaluationResult(BaseModel):
    """Represents the result of an evaluation process."""

    chain_of_thought_process: str = Field(
        ..., description="Detailed reasoning process used during evaluation"
    )
    place_to_reason: str = Field(
        ..., description="Location or reason for the evaluation"
    )

    list_of_quality_issues: list[QualityIssue] = Field(
        ..., description="List of identified quality issues in PRIMARY AI response only"
    )
    result: str = Field(..., description="Evaluation result: PASS OR FAIL")
    short_explanation: str = Field(
        ..., description="Brief explanation of the evaluation result"
    )


class IssueValidationResult(BaseModel):
    """Represents the result of validating a single issue."""
    chain_of_thought_process: str = Field(
        ..., description="Detailed reasoning process used during validation"
    )
    place_to_reason: str = Field(
        ..., description="Location or reason for the evaluation"
    )
    validation_result: str = Field(..., description="LEGITIMATE or FALSE POSITIVE")
    

class CombinerResult(BaseModel):
    """Represents the result of an combination process."""

    chain_of_thought_process: str = Field(
        ..., description="Detailed reasoning process used during evaluation"
    )
    place_to_reason: str = Field(
        ..., description="Location or reason for the evaluation"
    )

    list_of_quality_issues: list[QualityIssue] = Field(
        ..., description="List of identified quality issues"
    )