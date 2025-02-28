import json
import re
import traceback
import uuid

import gevent
import nbformat
import requests
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    HumanMessage,
)


from .Models.models import LLMModel, num_tokens_from_string
try:
    from app.logging_config import logger
except:
    pass


def display(content, color="red", id=None):
    # console.print(f"###{id}### " + content, style=color)
    print(f"###{id}### " + content)
    try:
        logger.info(f"###{id}### " + content)
    except:
        pass


supported_languages = [
    "python3",
    "php",
    "nodejs",
    "kotlin",
    "java",
    "go",
    "csharp",
    "cpp",
    "ruby",
    "swift",
    "haskell",
    "perl"
    
]


def extract_assistant_code_cells(notebook, loaded_notebook=None):
    
    print("NOTEBOOK: ", notebook)
    notebook_contents = [notebook]
    data = notebook_contents
    
    
    code_cells = []
    for item in data:
        conversation = item.get('conversation', [])
        for entry in conversation:
            if entry.get('role') == 'Assistant' and entry.get('type') == 'code':
                code_cells.append(entry.get('content'))
    return code_cells


def enforce_format(notebook_contents):
    note_json = json.loads(notebook_contents)
    current_speaker = ""
    extra_metadata = note_json["cells"][1]["source"][0]
    if not any(
        keyword in extra_metadata
        for keyword in ["**User**", "**Assistant**", "# Conversation"]
    ):
        note_json["cells"].pop(1)  # category cell
    cells = note_json["cells"]

    for n, cell in enumerate(cells):
        print(cell["source"])
        if "**User**" in cell["source"][0] or "# User" in cell["source"][0]:
            current_speaker = "**User**"
            print("SET SPEAKER TO: ", current_speaker)
            print("----")
            continue  # set current speaker and mover to next cell
        elif "**Assistant**" in cell["source"][0] or "# Assistant" in cell["source"][0]:
            current_speaker = "**Assistant**"
            print("SET SPEAKER TO: ", current_speaker)
            print("----")
            continue

        if current_speaker != "":
            other_form = "# " + current_speaker.split("**")[1]
            print(f"Current speaker: {current_speaker}")
            print(f"Cell content: {cells[n]['source'][0]}")
            print(f"Other form: {other_form}")
            cell_type = cells[n]["cell_type"]
            print(f"Cell type: {cell_type}")

            if (
                other_form in cells[n]["source"][0]
                or current_speaker in cells[n]["source"][0]
            ):
                pass
            else:
                if cell_type == "markdown":
                    print("INSERTING: ", current_speaker)
                    cells[n]["source"].insert(0, f"{current_speaker}\n")
                if cell_type == "code":
                    print("INSERTING: ", other_form)
                    cells[n]["source"].insert(0, f"{other_form}\n")

                print("NEW FULL CONTENT: ", cells[n]["source"])
        print("----")
    note_json["cells"] = cells
    return json.dumps(note_json)





def split_notebook_turns(notebook, loaded_notebook=None):
    print("NOTEBOOK: ", notebook)
    notebook_contents = [notebook]
    parsed_notebooks = notebook_contents
    turns = []
    conversation = parsed_notebooks[0]["conversation"]
    turn = []
    for i in range(len(conversation)):
        if conversation[i]["role"] == "User":
            if turn:
                turns.append(turn)
            turn = [
                {"role": conversation[i]["role"], "content": conversation[i]["content"]}
            ]
        elif conversation[i]["role"] == "Assistant":
            turn.append(
                {"role": conversation[i]["role"], "content": conversation[i]["content"]}
            )
        else:
            raise ValueError(
                f"Unexpected role found in conversation. {conversation[i]['role']}"
            )
    if turn:
        turns.append(turn)
        
        
        
    return turns


def load_notebook(path):
    with open(path) as f:
        nb = nbformat.read(f, as_version=4)
    return nb


def router(state):
    # This is the router
    messages = state["messages"]
    sender = state["sender"]
    last_message = messages[-1]

    if "function_call" in last_message.additional_kwargs:
        return "tool_node"  # irrespective of the sender
    else:
        return "END"


def create_json_for_code_api(code, language, dependencies, files):
    if language == "swift":
         return json.dumps({"code": code,"input": "None", "files":files})
    elif language == "python3":
        code = "def test_code():\n    " + code.replace("\n", "\n    ")
        code += "\n\n# R E A D M E\n# DO NOT CHANGE the code below, we use it to grade your submission. If changed your submission will be failed automatically.\nif __name__ == '__main__':  \n    test_code()" 
        return json.dumps({"code": code, "packages": dependencies, "input": "None", "files":files})
    else:
        return json.dumps({"code": code, "packages": dependencies, "input": "None", "files":files})


def make_code_exec_request(code, language, dependencies, files=[]):
   

    if dependencies:
        dependencies = " ".join(
            [dep if dep != "sklearn" else "scikit-learn" for dep in dependencies]
        )
    print(f"\n*****{dependencies}*****\n")
    url = "https://code-exec-server.xxxx.com/api/language/{language}/execute-code".format(
        language=language
    )
    json_body = create_json_for_code_api(code, language, dependencies, files)
    # print ("PRINTING CODE")

    request_id = uuid.uuid4()
    print(f"Request ID {request_id}: MAKING CES API REQUEST, JSON BODY: {json_body}")

    headers = {"Content-Type": "application/json"}
    response = None
    try:
        for attempt in range(3):  # Retry up to 2 times
            try:
                response = requests.post(
                    url, data=json_body, headers=headers, timeout=200
                )
                break  # Exit loop if request is successful
            except requests.exceptions.Timeout:
                gevent.sleep(0)
                if attempt < 2:
                    print(
                        f"Request ID {request_id}: Timeout occurred, retrying... (Attempt {attempt + 1}/3)"
                    )
                    continue  # Retry if timeout occurs
                else:
                    raise  # Raise exception if all retries fail

        print(f"Request ID {request_id}: CES API RESPONSE CODE: {response.status_code}")

        print(
            f"Request ID {request_id}: CES API RESPONSE PAYLOAD OK: {response.json()}"
        )

        def trim_value(value):
            if not value:
                return value
            Q = MAX_TOKENS // 3 * 4
            original_value = value
            while num_tokens_from_string(value) > MAX_TOKENS and Q > 0:
                value = (
                    original_value[:Q]
                    + "\n\nTHIS PART IS SKIPPED, TOO LONG...\n\n"
                    + original_value[-Q * 2 :]
                )
                Q -= 100
            if len(value) < len(original_value):
                print(
                    "OUTPUT CUTTING HAPPENED, TRIMMED FROM {} TO {}".format(
                        num_tokens_from_string(original_value),
                        num_tokens_from_string(value),
                    )
                )
            return value

        r = response.json()
        MAX_TOKENS = 3000

        def trim_dict_values(d):
            for key in ["out", "error"]:
                if key in d:
                    d[key] = trim_value(d[key])
            return d

        r = trim_dict_values(r)
        for k, v in r.items():
            if isinstance(v, dict):
                r[k] = trim_dict_values(v)
        return r
    except Exception as e:
        if response is not None and hasattr(response, "text"):
            print(
                f"Request ID {request_id}: Failed to parse response JSON. Response text: {response.text}"
            )
        else:
            traceback.print_exc()
        return f"An error occurred while executing code: {str(e)}"


def extract_dependencies(notebook_content, loaded_notebook=False) -> list:
    patterns = {
        "pip": r"pip install ([\w\-, ]+)",  # Python
        "npm": r"npm install ([\w\-, ]+)",  # Node.js
        "composer": r"composer require ([\w\-\/, ]+)",  # PHP
        "go": r"go get ([\w\-\/, ]+)",  # Go
        "gem": r"gem install ([\w\-, ]+)",  # Ruby
        "mvn": r"mvn install ([\w\-\.]+)",  # Maven (Java)
        "gradle": r"gradle add ([\w\-\.]+)",  # Gradle (Java/Kotlin)
        "swift": r"swift package add ([\w\-\.]+)",  # Swift
        "cabal": r"cabal install ([\w\-]+)",  # Haskell
    }
    if not loaded_notebook:
        dependencies = []
        for cell in notebook_content["cells"]:
            if cell["cell_type"] in ["code", "markdown"]:
                content = cell["source"]
                for manager, pattern in patterns.items():
                    matches = re.findall(pattern, content)
                    for match in matches:
                        dependencies.extend(re.split(r"[,\s]+", match.strip()))

        return dependencies

    else:
        dependencies = []
        for cell in notebook_content["conversation"]:
            content = cell["content"]
            for manager, pattern in patterns.items():
                matches = re.findall(pattern, content)
                for match in matches:
                    dependencies.extend(re.split(r"[,\s]+", match.strip()))

        return dependencies


class Runnable:
    def __init__(self, func):
        self.func = func

    def __or__(self, other):
        def chained_func(*args, **kwargs):
            # the other func consumes the result of this func
            return other(self.func(*args, **kwargs))

        return Runnable(chained_func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def group_turns(turns, dependencies):
    # Initialize a list to hold groups of dependent turns
    grouped_turns = []

    # Iterate through each dependency in the list
    for dep in dependencies["code_dependencies"]:
        # Extract the specific turns involved in the dependency
        turn_group = [turns[i - 1] for i in dep["dependencies"]]
        # Append the group to the list of grouped turns
        grouped_turns.append(turn_group)

    return grouped_turns

