from typing import Dict, List, Optional
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class InputData(BaseModel):
    messages: List[Message]
    tools: Optional[List[Dict]] = None
    stream: bool = False
    tool_choice: str = "auto"


class EvaluationConfig(BaseModel):
    api_key: str
    provider: str
    model: str = None
    temperature: float = None
    seed: int = None


class PassThroughRequest(BaseModel):
    inputs: List[InputData]
    evaluations: List[Dict] = None
