import json

from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.messages import AIMessage, FunctionMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .Models.models import LLMModel
from .tools import all_schema as schemas
from .utils import Runnable, supported_languages

default_instructions = f"""<|INSTRUCTIONS START|>
Your role involves the following steps:
1. You will be given a piece of code along with a test scenario, which could be a happy path or an edge case.
2. Your task is to write the test code and combine it with the original code to form a complete script.
##dummy_files
4. Execute the complete code and test using the ExecuteCodeTool tool. This approach eliminates the need for any unit test framework.
5. If you encounter any issues after invoking any tool, feel free to make necessary corrections and retry.
6. To minimize token consumption, ensure your test codes limit output verbosity by avoiding excessive or unnecessary printing of data and lengthy strings.
<|INSTRUCTIONS END|>
<|ENFORCE START|>
NOTE: Do whatever you need to do and only give your final comment when done.
Remember, always write a complete code that can be executed as a standalone script. 
Do not modify the original code provided (just add your tests), use exactly as received even if it contains syntax error or any other form of error.
NOTE: make use of print within your code to output information for better observation and debugging.
NOTE: Avoid using 'if __name__ == '__main__' in python3 codes as this will prevent the code from running.
When including backslashes (\\) in code, such as in print statements, 
ensure you escape them by adding an additional backslash. For example, 
use print("hello, \\\\n") to correctly insert a newline character in the output of the print, 
rather than the code itself.
<|ENFORCE END|>
<|AVAILABLE OUTPUT TOOLS START|>
TestResults - Call it when you need to provide the final report.
ExecuteCodeTool - Call it to run and rerun the code.
<|AVAILABLE OUTPUT TOOLS END|>
<|AVAILABLE LANGUAGE VALUES START|>
{supported_languages}
<|AVAILABLE LANGUAGE VALUES END|>
ALWAYS CALL AT LEAST AND AT MOST ONE TOOL. ONE TOOL ALWAYS!
YOUR OUTPUT IS A JSON!
ALL FIELDS IN THE CHOSEN TOOL MUST ALWAYS BE PROVIDED!
PAY ATTENTION TO COMMAS AFTER EACH JSON VALUE WHERE NEEDED!
IF YOU ENCOUNTER CODE RUN TIMEOUT OR A PROBLEM THAT CAN'T BE AVOIDED, STOP TRYING AND OUTPUT TEST RESULTS WITH FAIL
YOU WILL NOT MODIFY THE ORIGINAL CODE PROVIDED (YOU WILL JUST ADD YOUR TESTS), YOU WILL USE EXACTLY AS RECEIVED EVEN IF IT CONTAINS SYNTAX ERROR OR ANY OTHER FORM OF ERROR. YOU WILL TREAT AS CODE EVERYTHING PROVIDED INSIDE CODE START AND CODE END TAGS EVEN IF IT CONTAINS NON-CODE BECAUSE THE USER THINKS IT'S THE CODE TO BE TESTED, SO YOU WILL TEST IT AS IS.
"""


# INT APPLE EVALUATOR
default_interpreter = f"""<|INSTRUCTIONS START|>
Your role involves the following steps:
1. You will be given a piece of code, and the output of the execution.
2. Report whether the code ran successfully without any errors or not (YES or NO).
"""


class CodeExecutionReport(BaseModel):
    """Represents the report of the code execution."""

    result: str = Field(
        ..., description="if The code ran successfully, either YES or NO."
    )
    comment: str = Field(
        ..., description="Any comments or notes about the code result."
    )


# default_interpreter = f"""<|INSTRUCTIONS START|>
# Your role involves the following steps:
# 1. You will be given a piece of code.
# 2. Your task is to run the code as is, without any modifications.
# 3. Report whether the code ran successfully without any errors.
# <|INSTRUCTIONS END|>
# <|ENFORCE START|>
# NOTE: Do whatever you need to do and only give your final comment when done.
# Remember, always write a complete code that can be executed as a standalone script.
# Do not modify the original code provided (just add your tests), use exactly as received even if it contains syntax error or any other form of error.
# NOTE: make use of print within your code to output information for better observation and debugging.
# NOTE: Avoid using 'if __name__ == '__main__' in python3 codes as this will prevent the code from running.
# When including backslashes (\\) in code, such as in print statements,
# ensure you escape them by adding an additional backslash. For example,
# use print("hello, \\\\n") to correctly insert a newline character in the output of the print,
# rather than the code itself.
# <|ENFORCE END|>
# <|AVAILABLE OUTPUT TOOLS START|>
# ExecuteCodeTool - Use this tool to run the code.
# TestResults - Use this tool to report the execution outcome.
# <|AVAILABLE OUTPUT TOOLS END|>
# <|AVAILABLE LANGUAGE VALUES START|>
# {supported_languages}
# <|AVAILABLE LANGUAGE VALUES END|>
# ALWAYS CALL AT LEAST AND AT MOST ONE TOOL. ONE TOOL ALWAYS!
# ALL FIELDS IN THE CHOSEN TOOL MUST ALWAYS BE PROVIDED!
# IF YOU ENCOUNTER CODE RUN TIMEOUT OR A PROBLEM THAT CAN'T BE AVOIDED, STOP TRYING AND OUTPUT TEST RESULTS WITH FAIL.
# """


class CodeRunner:
    def __init__(
        self, provider, fix_output=False, use_dummy_files=True, interpreter_mode=False
    ):

        # SYSTEM PROMPT CONFIG
        if not interpreter_mode:
            if use_dummy_files:
                self.dummy_file_instructions = "3. If the test requires dummy files such as JSON or CSV or needs to create directory or files, do everything within the test code by code."
            else:
                self.dummy_file_instructions = "3. necessary files needed within the code will be available in the machine executing the code"

            self.main_instruction = default_instructions
            self.main_instruction.replace("##dummy_files", self.dummy_file_instructions)
            self.schemas = schemas
            self.tools_string = "TestResults or ExecuteCodeTool."

        elif interpreter_mode:
            self.main_instruction = default_interpreter
            self.schemas = [CodeExecutionReport]
            self.tools_string = "CodeExecutionReport"

        self.provider = provider
        self.fix_output = fix_output
        self.code_runner_llm_openai = LLMModel(
            provider="openai_api",
            model="gpt-4o",
            config={
                "model_kwargs": {
                    "tool_choice": "required",
                    "parallel_tool_calls": False,
                },
                "params": {"temperature": 0.1},
            },
        ).create_model()
        self.code_runner_llm_anthropic = LLMModel(
            provider="anthropic_api", model="claude-3-5-sonnet-20240620"
        ).create_model()
        self.corrector_chain_openai = self._build_corrector_chain(
            self.code_runner_llm_openai
        )
        self.corrector_chain_anthropic = self._build_corrector_chain(
            self.code_runner_llm_anthropic
        )
        self.code_runner_chain_openai = self._build_code_runner_chain(
            self.code_runner_llm_openai, self.corrector_chain_openai
        )
        self.code_runner_chain_anthropic = self._build_code_runner_chain(
            self.code_runner_llm_anthropic, self.corrector_chain_anthropic
        )

    def _build_corrector_chain(self, llm_model):
        corrector_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Your only job is to get the user message use it to call one of the following tool:\n"
                    "{tools}\n"
                    "One of the tool must be used"
                    "Nothing Else is Expected from you.",
                ),
                ("human", "{original_message}"),
            ]
        )
        corrector_prompt = corrector_prompt.partial(tools=self.tools_string)
        return corrector_prompt | llm_model.bind_tools(self.schemas)

    def _build_code_runner_chain(self, llm_model, corrector_chain):
        code_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""As a seasoned developer, you are known as code_runner.\n{self.main_instruction}""",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        if self.fix_output:
            code_runner_chain = (
                code_prompt
                | llm_model.bind_tools(self.schemas)
                | Runnable(self.fix_output_function)
                | PydanticToolsParser(tools=self.schemas)
            )
        else:
            code_runner_chain = (
                code_prompt
                | llm_model.bind_tools(self.schemas)
                | PydanticToolsParser(tools=self.schemas)
            )
        return code_runner_chain.with_retry(stop_after_attempt=5)

    def fix_output_function(self, original_input):
        parser = PydanticToolsParser(tools=self.schemas)
        try:
            rx = parser.invoke(original_input)
            rx[-1]
            print("got here!:", rx)
            return original_input
        except Exception as e:
            # this could be caused by wrong schema in function call or llm output AIMessage
            content = original_input.content
            function_call = original_input.additional_kwargs.get("tool_calls")
            if function_call:
                function_call = [a["function"]["arguments"] for a in function_call]
                function_call = "\n".join(function_call)
            final_content = (
                f"{content} \n {function_call}" if function_call else content
            )
            print("I had to correct:", final_content)

            # use LLM to correct
            corrector_chain = (
                self.corrector_chain_openai
                if self.provider == "openai_api"
                else self.corrector_chain_anthropic
            )
            return corrector_chain.invoke(input={"original_message": final_content})

    def __call__(self, state):
        print("INVOKING WITH:", state["messages"])
        code_runner_chain = (
            self.code_runner_chain_openai
            if self.provider == "openai_api"
            else self.code_runner_chain_anthropic
        )
        in_ = state["messages"]
        if self.provider == "anthropic_api":
            in_new = []
            for i, m in enumerate(in_):
                if isinstance(m, FunctionMessage):
                    in_new.append(HumanMessage(m.content))
                else:
                    in_new.append(m)
            in_ = in_new
        out = code_runner_chain.invoke(in_)
        print("\n", "INVOKE OUT:", out, "\n")
        tool_name = out[-1].__class__.__name__

        if tool_name == "CodeExecutionReport":
            return out[-1].dict()

        elif tool_name != "TestResults":
            ak = {
                "function_call": {
                    "arguments": json.dumps(out[-1].dict()),
                    "name": tool_name,
                }
            }
            if self.provider == "anthropic_api":
                content = "I will call the ExecuteCode Function to Run the code"
            else:
                content = ""
            message = [AIMessage(content=content, additional_kwargs=ak)]

        else:
            content = json.dumps(out[-1].dict())
            message = [AIMessage(content=content)]
        return {
            "messages": message,
            "sender": "code_runner",
        }
