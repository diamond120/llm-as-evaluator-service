import copy
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import nbformat
from fuzzywuzzy import fuzz
from tqdm.auto import tqdm

from extra.parsers.fix_roles import LLMCellRoleFixer


class Parser:
    def __init__(self, user="User", assistant="Assistant", max_workers=10):
        self.max_workers = max_workers
        self.role_fixer = LLMCellRoleFixer(user=user, assistant=assistant)
        self.user = user
        self.assistant = assistant

    def get_closest_match(self, query, choices):
        """
        Get the closest match(es) to a query string from a list of choices.

        :param query: The query string.
        :param choices: A list of strings to match against.
        :param limit: The maximum number of matches to return.
        """
        best_role = None
        best_score = 0
        for choice in choices:
            score = fuzz.ratio(query, choice)
            if score > best_score and score > 25:
                best_score = score
                best_role = choice

        return best_role, best_score

    def count_empty_from_end(self, cells):
        count = 0
        for message in reversed(cells):
            if message["source"].strip() == "":
                count += 1
            else:
                break
        return count

    def extract_messages(self, notebook):
        """
        Parse a notebook and extract the message objects.

        :param notebook: The notebook object.
        """
        messages = []
        cut_tail = self.count_empty_from_end(notebook.cells)
        cells = notebook.cells[2:]
        if cut_tail:
            cells = cells[:-cut_tail]
        for pos, cell in enumerate(cells, start=1):
            if cell["cell_type"] == "markdown":
                headers = [f"**{self.user}**", f"**{self.assistant}**"]
            elif cell["cell_type"] == "code":
                headers = [f"# {self.user}", f"# {self.assistant}"]
            else:
                raise Exception(f'Unknown cell type {cell["cell_type"]}')

            lines = cell["source"].split("\n")
            first_line = lines[0]
            role, score = self.get_closest_match(first_line, headers)
            if score > 50:
                valid_role = role.replace("*", "").replace("#", "").strip()
                content = "\n".join(lines).strip("\n")
            else:
                valid_role = ""
                content = cell["source"]
            message = {
                "cell_pos": pos,
                "role": valid_role,
                "content": content,
                "type": cell["cell_type"],
            }
            messages.append(message)

        return messages

    def extract_metadata(self, notebook):
        # # Extract the first cell
        first_cell = notebook.cells[0]["source"]

        return {"metadata": first_cell}

    def notebook_parser(self, content: str):
        # version is hardcoded, WARNING
        nb_parsed_notebook = nbformat.reads(content, as_version=4)
        messages, metadata = None, None
        messages = self.extract_messages(nb_parsed_notebook)
        metadata = self.extract_metadata(nb_parsed_notebook)
        messages, errors = self.role_fixer.fix_missing_roles(messages)
        if errors:
            raise Exception("Failed to predict missing roles.")
        return {
            "status": "OK",
            "metadata": metadata,
            "conversation": messages,
        }

    def parse_notebooks(self, input_batch):
        input_batch = copy.deepcopy(input_batch)

        def parse_content(item):
            if item["content"]:
                return self.notebook_parser(item["content"])
            return {
                "status": "NONE",
            }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(parse_content, item): item
                for item in input_batch["items"]
            }
            for future in tqdm(
                as_completed(futures), desc="Parsing notebooks", total=len(futures)
            ):
                item = futures[future]
                try:
                    item["parsed"] = future.result()
                except Exception as exc:
                    print(f"Generated an exception: {exc}")
                    item["parsed"] = {
                        "status": "FAILED",
                        "error_msg": str(exc),
                    }
        return input_batch

    def split_messages_into_turns(self, messages):
        turns = []
        current_role_steps = []
        if not messages:
            return {
                "status": "ERROR",
                "reason": "No messages were provided to turn splitter.",
            }

        current_role = messages[0]["role"]
        for message in messages:
            role = message["role"]
            if current_role != role:
                turns.append({"role": current_role, "steps": current_role_steps})
                current_role_steps = []
                current_role = role
            current_role_steps.append(
                {"type": message["type"], "content": message["content"]}
            )
        if current_role_steps:
            turns.append({"role": current_role, "steps": current_role_steps})

        for turn in turns:
            if turn["role"] == self.assistant:
                turn["role"] = self.assistant
            elif turn["role"] == self.user:
                turn["role"] = self.user
            else:
                return {"status": "ERROR", "reason": "Contains unrecognized header"}

        grouped_turns = []
        for i in range(0, len(turns), 2):
            group = turns[i : i + 2]
            grouped_turns.append(group)
        return {"status": "OK", "turns": grouped_turns}

    def notebook_to_turns(self, notebook):
        parsed_notebook = {**self.notebook_parser(notebook)}
        turns = self.split_messages_into_turns(parsed_notebook["messages"])
        if turns["status"] == "OK":
            return turns["turns"]
        else:
            raise Exception("Bad notebook")
