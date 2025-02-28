

from enum import Enum
from typing import Annotated, List, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
import operator
from .utils import make_code_exec_request, supported_languages


#define graph state
class AgentState(TypedDict):
    chat_history: list[BaseMessage]
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender: str
    user_config:dict


class Code(BaseModel):
    code: str = Field(description=" complete code to be executed")

class Severity(Enum):
    CRITICAL = "Critical"
    MEDIUM = "Medium"
    LOW = "Low"

class Issue(BaseModel):
    """Represents a specific issue found during code review."""

    cell_position: int = Field(
        ..., description="The position of the cell where the issue was found."
    )
    what: str = Field(..., description="A brief description of the issue.")
    why: str = Field(..., description="Explanation of why this is an issue.")
    where: str = Field(
        ...,
        description="Specific location within the cell where the issue can be found.",
    )
    severity: Severity = Field(
        ...,
        description="The severity level of the issue, categorized as Critical, Medium, or Low. Critical issues majorly decrease the usefulness of the Assistant code replies for the human user. Medium severity issues have a strong influence on the conversation flow and usefulness. Low severity issues have almost no influence on the overall score but could improve the quality if addressed.",
    )
    fix: str = Field(
        ..., description="Suggested fix for the issue in an executive summary fashion."
    )

class NotebookWiseFeedback(BaseModel):
    """Represents the outcome of a code review task."""

    scratchpad: str = Field(
        ...,
        description="Place for you to think. Think before issues and score creation. Be concise. Analyze the text to achieve your goal. Always think before looking for issues!",
    )
    issues: list[Issue] = Field(
        ...,
        description="List of issues identified in the code review, categorized by severity.",
    )
    scoring_explanation: str = Field(
        ...,
        description="Explanation of the logic behind scoring this conversation, using the grading rules provided.",
    )
    score: int | None = Field(
        ...,
        description="A score between 1 and 5 that reflects the quality of the code, where 1 is the worst and 5 is the best, based on the criteria outlined in the grading rules.",
    )



class TestResult(Enum):
    PASSED = "Passed"
    FAILED = "Failed"

class TestResults(BaseModel):
    """Represents the outcome of a test."""
    result: str = Field(
        ..., description="The result of the test, either PASSED or FAILED."
    )
    comment: str = Field(
        ..., description="Any comments or notes about the test result."
    )


#Nodes Output schema
class StandardResponse(BaseModel):
    """Represents a standard response from the agent/ai."""
    response: str = Field(description="your actual response/answer in markdown format")
    sender: str = Field(description="your name in lowercase")
    directed_to: str = Field(description="your response must be directed to another agent or to human")
    
    
    
#Testers Output schema
class Issues(BaseModel):
    """Represents a list of potential issues."""
    issues: List[Issue] = Field(description="List of potential issues")


class HappyPaths(BaseModel):
    """Represents a list of happy paths."""
    happy_paths: List[str] = Field(description="List of happy paths. Should not be numbered")
    code: str = Field(description="The original code given to you")

class EdgeCases(BaseModel):
    """Represents a list of edge cases."""
    edge_cases: List[str] = Field(description="List of edge cases.  Should not be numbered")
    
    
class TurnClassification(BaseModel):
    """TurnClassification"""
    has_code: bool = Field(..., description="Indicates if the turn has code")
    complete_code: bool = Field(..., description="Indicates if the code is complete and can be executed independently")
    can_be_tested: bool = Field(..., description="Indicates if the code can be tested")
    reason_it_cant_be_tested: str = Field(..., description="The reason why the code cannot be tested if it cant be. eg syntax error or missing import")
    code: str = Field(..., description="The actual code as a string")
    dependencies: List[str] = Field(..., description="List of dependencies required for the code")
    language: str = Field(..., description=f"the programming language the code is written in. It must be any of the following {supported_languages}")




class TurnClassificationNoCorrections(BaseModel):
    """TurnClassification"""
    has_code: bool = Field(..., description="Indicates if the turn has code")
    complete_code: bool = Field(..., description="Indicates if the code is complete and can be executed independently")
    can_be_tested: bool = Field(..., description="Indicates if the code can be tested. This should be false if there are errors like syntax, indentation, missing import etc")
    reason_it_cant_be_tested: str = Field(..., description="The reason why the code cannot be tested if it cant be. eg syntax error, wrong indentation or missing import")
    # code: str = Field(..., description="The actual code as a string")
    dependencies: List[str] = Field(..., description="List of dependencies required for the code")
    language: str = Field(..., description=f"the programming language the code is written in. It must be any of the following {supported_languages}")


class CodeDependency(BaseModel):
    """CodeDependency"""
    dependencies: List[int] = Field(..., description="Indicates the turn dependencies")
    comment: str = Field(..., description="comment on why it they depend on each other")
   
class CodeDependencyList(BaseModel):
    """CodeDependencyList"""
    code_dependencies: List[CodeDependency] = Field(..., description="List of code dependencies")

