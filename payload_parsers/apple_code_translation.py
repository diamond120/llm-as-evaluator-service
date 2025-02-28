import logging
import os
import re
import traceback
from dataclasses import dataclass, field

from tqdm import tnrange

from app.logging_config import logger


@dataclass
class TranslationNotebook:
    user_message: str = ""
    user_message_python: str = ""
    user_message_swift: str = ""
    solution_description: str = ""
    python_messages: list = field(default_factory=list)
    swift_messages: list = field(default_factory=list)
    notebook_metadata: dict = field(default_factory=dict)
    deliverable_id: str = ""
    annotator_ids: list = field(default_factory=list)

    @property
    def conversation(self):
        return {
            "language": {"overall": "en_US"},
            "notes": {
                "task_category_list": ["Coding"],
                "annotator_ids": self.annotator_ids,
                "notebook_metadata": self.notebook_metadata,
            },
            "messages": [
                {
                    "_message_type": "MessageBranch",
                    "choices": [
                        {
                            "response_source": "Python_3.10",
                            "messages": [
                                {
                                    "role": "user",
                                    "contents": [{"text": self.user_message}],
                                },
                                {
                                    "role": "assistant",
                                    "contents": [{"text": self.solution_description}]
                                    + self.python_messages,
                                },
                            ],
                        },
                        {
                            "response_source": "Swift_5",
                            "messages": [
                                {
                                    "role": "user",
                                    "contents": [{"text": self.user_message}],
                                },
                                {
                                    "role": "assistant",
                                    "contents": [{"text": self.solution_description}]
                                    + self.swift_messages,
                                },
                            ],
                        },
                    ],
                }
            ],
        }

    def clean_text(self, text):
        # Remove specific annotations
        return (
            text.replace("# Solution", "")
            .replace("# Prompt:", "")
            .replace("# Prompt", "")
            .replace("**Prompt:** -", "")
            .replace("**Assistant**", "")
            .replace("# Metadata", "")
            .strip()
        )

    def normalize_language(self, language_version):
        """Normalize the language to 'python' or 'swift' regardless of version."""
        if language_version.lower().startswith("python"):
            return "python"
        elif language_version.lower().startswith("swift"):
            return "swift"
        return language_version.lower()

    def parse_metadata_cell(self, cell):
        """Parse the metadata cell to extract required information into a JSON object."""
        metadata_text = "".join(cell["content"])
        metadata_lines = metadata_text.split("\n")
        json_obj = {}
        regex = re.compile(r"(?<!\*)\*\*(?!\*)(.+?)\*\*(?!\*):?\s*-?\s*(.*)")

        for line in metadata_lines:
            match = regex.match(line.strip())
            if match:
                key, value = match.groups()
                key = key.strip().replace(
                    ":", ""
                )  # Remove colons from the key if it exists
                if key.strip().lower() not in ["example", "starter code"]:
                    json_obj[key.strip()] = value.strip()
        return json_obj

    def extract_message_branch(self, notebook):
        current_language = None
        python_starter_code = ""
        swift_starter_code = ""
        regex_remove = re.compile(
            r"\*\*(keywords:|keywords|keywords|key words|difficulty level|difficulty|difficulty level|difficulty level:)\*\*:?.*",
            re.IGNORECASE,
        )

        for cell in notebook:
            if cell["type"] == "markdown":
                cell_source = self.clean_text("".join(cell["content"]).strip())
                cell_source = re.sub(regex_remove, "", cell_source)
                if not self.user_message:
                    self.notebook_metadata = self.parse_metadata_cell(cell)
                    self.user_message = cell_source
                    # Regex patterns to extract Python and Swift code blocks from the user message
                    python_code_match = re.search(
                        r"```python(.+?)```", self.user_message, re.DOTALL
                    )
                    swift_code_match = re.search(
                        r"```swift(.+?)```", self.user_message, re.DOTALL
                    )

                    # If we have a Python code block, create the Python starter code
                    if python_code_match:
                        python_starter_code = (
                            "```python\n" + python_code_match.group(1).strip() + "\n```"
                        )

                    # If we have a Swift code block, create the Swift starter code
                    if swift_code_match:
                        swift_starter_code = (
                            "```swift\n" + swift_code_match.group(1).strip() + "\n```"
                        )

                    # Remove starter codes from the general user message
                    self.user_message = re.sub(
                        r"```python(.+?)```", "", self.user_message, flags=re.DOTALL
                    ).strip()
                    self.user_message = re.sub(
                        r"```swift(.+?)```", "", self.user_message, flags=re.DOTALL
                    ).strip()

                    # Append the respective starter code to the user message for each language
                    self.user_message_python = (
                        self.user_message + "\n\n" + python_starter_code
                    )
                    self.user_message_swift = (
                        self.user_message + "\n\n" + swift_starter_code
                    )
                elif not self.solution_description:
                    self.solution_description = cell_source
                elif "# Python Answer" in cell_source:
                    current_language = "Python"
                elif "# Swift Answer" in cell_source:
                    current_language = "Swift"
            elif cell["type"] == "code":
                code_content = "".join(cell["content"]).strip()
                if current_language == "Python":
                    self.python_messages.append(
                        {"text": "```python\n" + code_content + "\n```"}
                    )
                elif current_language == "Swift":
                    self.swift_messages.append(
                        {"text": "```swift\n" + code_content + "\n```"}
                    )

    def extract_code(self, contents):
        solution_blocks = []
        test_blocks = []

        # Assume the first code block is the solution and the second is the test
        code_blocks = [block["text"] for block in contents if "```" in block["text"]]

        if code_blocks:
            # The first block is the solution
            solution_blocks.append(self.strip_backticks(code_blocks[0]))

            # The second block is the test (if it exists)
            if len(code_blocks) > 1:
                test_blocks.append(self.strip_backticks(code_blocks[1]))

        combined_code = "\n".join(solution_blocks + test_blocks)
        return combined_code

    def strip_backticks(self, code):
        stripped_code = re.sub(
            r"```(\w+)?\n", "", code
        )  # Remove the opening ``` and the language identifier
        stripped_code = stripped_code.replace("```", "")  # Remove the closing ```
        return stripped_code


def parse_payload(json_array: list[dict]):
    tn = TranslationNotebook()
    tn.extract_message_branch(json_array)
    c = tn.conversation
    return {
        "user_message": tn.user_message,
        "solution_description": tn.solution_description,
        "src": {
            "language": tn.normalize_language(
                c["messages"][0]["choices"][0]["response_source"]
            ),
            "user_message": tn.user_message_python,
            "code": tn.extract_code(
                c["messages"][0]["choices"][0]["messages"][1]["contents"]
            ),
        },
        "dest": {
            "language": tn.normalize_language(
                c["messages"][0]["choices"][1]["response_source"]
            ),
            "user_message": tn.user_message_swift,
            "code": tn.extract_code(
                c["messages"][0]["choices"][1]["messages"][1]["contents"]
            ),
        },
    }
