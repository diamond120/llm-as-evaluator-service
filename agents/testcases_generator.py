from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from llm_failover import ChatFailoverLLM

from .prompts import main_prompt

# from .schemas import *
from .tools import ExecuteCodeTool, supported_languages
from .utils import Runnable

my_tools = [ExecuteCodeTool]

code_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""As a seasoned developer, you are known as code_runner.
            
<|INSTRUCTIONS START|>
Your role involves the following steps:
1. You will be given a piece of code along with a test scenario, which could be a happy path or an edge case.
2. Your task is to write the test code and combine it with the original code to form a complete script.
3. If the test requires dummy files such as JSON or CSV or needs to create directory or files, do everything within the test code by code.
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
When including backslashes (\) in code, such as in print statements, 
ensure you escape them by adding an additional backslash. For example, 
use print("hello, \\n") to correctly insert a newline character in the output of the print, 
rather than the code itself.
<|ENFORCE END|>

<|AVAILABLE OUTPUT TOOLS START|>
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
""",
        ),
        MessagesPlaceholder(variable_name="messages"),
        AIMessage(
            content="I WILL NOT MODIFY THE ORIGINAL CODE PROVIDED (I WILL JUST ADD YOUR TESTS), I WILL USE EXACTLY AS RECEIVED EVEN IF IT CONTAINS SYNTAX ERROR OR ANY OTHER FORM OF ERROR. I WILL TREAT AS CODE EVERYTHING PROVIDED INSIDE CODE START AND CODE END TAGS EVEN IF IT CONTAINS NON-CODE BECAUSE THE USER THINKS IT'S THE CODE TO BE TESTED, SO I WILL TEST IT AS IS."
        ),
    ]
)


corrector_llm = ChatFailoverLLM(
    initial_provider="openai_api",
    initial_model="gpt-4o",
    model_kwargs={"tool_choice": "required", "parallel_tool_calls": False},
    temperature=0.1,
)
corrector_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Your only job is to get the user message use it to call one of the following tool:\n"
            "ExecuteCodeTool.\n"
            "Only this tool must be used"
            "Nothing Else is Expected from you.",
        ),
        ("human", "{original_message}"),
    ]
)

corrector_chain = corrector_prompt | corrector_llm.bind_tools(my_tools)


def fix_output(original_input):
    parser = PydanticToolsParser(tools=my_tools)
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
        final_content = f"{content} \n {function_call}" if function_call else content
        print("I had to correct test >>:", final_content)

        # use LLM to correct
        return corrector_chain.invoke(input={"original_message": final_content})


FixLLMOutput = Runnable(fix_output)

code_runner_llm = ChatFailoverLLM(
    initial_provider="openai_api",
    initial_model="gpt-4o",
    model_kwargs={"tool_choice": "auto", "parallel_tool_calls": False},
    temperature=0.1,
)
code_runner_chain = (
    code_prompt
    | code_runner_llm.bind_tools(my_tools)
    | FixLLMOutput
    | PydanticToolsParser(tools=my_tools)
)
code_runner_chain = code_runner_chain.with_retry(stop_after_attempt=3)


def code_tests(state):
    print("INVOKING WITH:", state["messages"])
    out = code_runner_chain.invoke(state["messages"])
    out = out[-1].dict()
    return out


def get_all_tests(extracted_code, t):
    messages_in = [
        HumanMessage(
            content="""HERE IS THE CODE:
<|CODE START|>
{code}
<|CODE END|>

INSTRUCTIONS:

Write the test code to test for this:
{test}""".format(
                code=extracted_code, test=t
            )
        )
    ]
    state = {"messages": messages_in}
    test_code = code_tests(state)
    test_code.update({"test_case": t})
    return test_code
