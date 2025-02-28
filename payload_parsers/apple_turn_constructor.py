import dataclasses
import enum
import re
from functools import cached_property
from typing import Dict, List, Optional

from app.logging_config import logger

# Regular Expressions to identify the start of user and assistant roles
ROLE_START_REGEX = re.compile(
    r"^\s*\*\*(?P<role_start>user|assistant)\*\*", re.IGNORECASE
)
SYSTEM_START_REGEX = re.compile(r"^\s*\*\*system\*\*", re.IGNORECASE)
NOEXPORT_REGEX = re.compile(r"^\s*#\s*NOEXPORT", re.IGNORECASE)
METADATA_REGEX = re.compile(r"^\s*#\s*Metadata", re.IGNORECASE)
CONVERSATION_REGEX = re.compile(r"^\s*#\s*Conversation", re.IGNORECASE)


class CellKind(enum.Enum):
    assistant_start = enum.auto()
    user_start = enum.auto()
    regular = enum.auto()
    code = enum.auto()
    noexport = enum.auto()
    metadata = enum.auto()
    conversation = enum.auto()


ROLE_START_KIND = {
    "User": CellKind.user_start,
    "Assistant": CellKind.assistant_start,
}


@dataclasses.dataclass
class CellData:
    id: str
    content: str
    cell_type: str

    @cached_property
    def kind(self) -> CellKind:
        if self.cell_type == "markdown":
            if mo := ROLE_START_REGEX.match(self.content):
                role_start = mo.groupdict()["role_start"]
                if role_start.lower() == "user" and role_start != "User":
                    raise ValueError(f"Invalid role start: {role_start}")
                if role_start.lower() == "assistant" and role_start != "Assistant":
                    raise ValueError(f"Invalid role start: {role_start}")
                return ROLE_START_KIND[role_start.capitalize()]
            elif SYSTEM_START_REGEX.match(self.content):
                return CellKind.metadata
            elif METADATA_REGEX.match(self.content):
                return CellKind.metadata
            elif CONVERSATION_REGEX.match(self.content):
                return CellKind.conversation
            elif NOEXPORT_REGEX.match(self.content):
                return CellKind.noexport
            else:
                return CellKind.regular
        elif self.cell_type == "code":
            return CellKind.code
        else:
            raise ValueError(f"Unknown cell type {self.cell_type}")

    @classmethod
    def from_json(cls, cell):
        cell_id = cell.get("id")
        return cls(
            content=cell["content"],
            cell_type=cell["type"],
            id=cell_id,
        )


@dataclasses.dataclass
class Turn:
    user: "list[CellData]" = dataclasses.field(default_factory=list)
    assistant: "list[CellData]" = dataclasses.field(default_factory=list)
    order: "list[tuple[CellKind, CellData]]" = dataclasses.field(default_factory=list)

    def extract_responses(self):
        user_prompts = "\n\n".join([cell.content for cell in self.user])
        assistant_responses = "\n\n".join([cell.content for cell in self.assistant])
        assistant_code = "\n\n".join(
            [cell.content for cell in self.assistant if cell.cell_type == "code"]
        )
        assistant_text = "\n\n".join(
            [cell.content for cell in self.assistant if cell.cell_type != "code"]
        )
        combined_turn = f"User prompt:\n{user_prompts}\n\nAssistant response:\n{assistant_responses}"

        return {
            "user_prompts": user_prompts,
            "assistant_responses": assistant_responses,
            "assistant_code": assistant_code,
            "assistant_text": assistant_text,
            "combined_turn": combined_turn,
        }


def parse_payload(json_array: List[Dict]):
    cells = [CellData.from_json(cell) for cell in json_array]
    conversation = []
    turn: Optional[Turn] = None

    def contains_ignored_kinds(turn: Turn) -> bool:
        return any(
            cell.kind in {CellKind.metadata, CellKind.conversation}
            for _, cell in turn.order
        )

    for cell in cells:
        if cell.kind == CellKind.noexport:
            continue
        elif cell.kind == CellKind.user_start:
            if turn and not contains_ignored_kinds(turn):
                conversation.append(turn)
            turn = Turn(user=[cell])
            turn.order.append((CellKind.user_start, cell))
        elif cell.kind == CellKind.assistant_start:
            if not turn:
                turn = Turn()
            turn.assistant.append(cell)
            turn.order.append((CellKind.assistant_start, cell))
        elif cell.kind in (CellKind.code, CellKind.regular):
            if not turn:
                turn = Turn()
            if cell.kind == CellKind.code:
                turn.assistant.append(cell)
            elif turn and cell.kind == CellKind.regular:
                turn.assistant.append(cell)
            turn.order.append((cell.kind, cell))
    if turn and not contains_ignored_kinds(turn):
        conversation.append(turn)
    logger.debug("AAAAAA" + str([t.extract_responses() for t in conversation]))
    return {"conversation": [t.extract_responses() for t in conversation]}
