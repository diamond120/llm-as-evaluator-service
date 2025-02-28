from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .Models.models import LLMModel
from .prompts import main_prompt
from .schemas import (
    CodeDependencyList,
    EdgeCases,
    HappyPaths,
    Issues,
    NotebookWiseFeedback,
    StandardResponse,
    TurnClassification,
    TurnClassificationNoCorrections,
)


# Base Prompt Template
def get_base_prompt_template(name=None, custom_instructions=None, agents=None):
    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Your name is {name} and you are working along side other agents as listed below\n"
                "Agents: \n {agents}\n\n\n "
                "{custom_instructions}\n\n\n"
                "ALWAYS CALL AT LEAST AND AT MOST ONE TOOL. ONE TOOL ALWAYS!\n"
                "YOUR OUTPUT IS A JSON!\n"
                "ALL FIELDS IN THE CHOSEN TOOL MUST ALWAYS BE PROVIDED!\n"
                "PAY ATTENTION TO COMMAS AFTER EACH JSON VALUE WHERE NEEDED!",
            )
        ]
    )

    prompt_template = prompt_template.partial(name=name)
    prompt_template = prompt_template.partial(agents=agents)
    prompt_template = prompt_template.partial(
        custom_instructions=custom_instructions if custom_instructions else ""
    )
    return prompt_template


# CODE EXTRACTORS
code_extractor_prompt_template = get_base_prompt_template(
    name="code_extractor",
    custom_instructions="Your role is to extract the code provided by the AI assistant from the conversation in the notebook. "
    "Once you've extracted the code, forward it to the agent named testers without making any changes. ",
    agents="testers",
)

code_extractor = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    use_history=False,
    # use_tool=False,
    output_schema=StandardResponse.model_json_schema(),
    prompt_template=code_extractor_prompt_template,
    config={"retry": 3},
)


# Happy Pather Agent
happy_pather_prompt_template = get_base_prompt_template(
    name="happy_pather aka testers",
    custom_instructions="Your role is to generate and list (Just 10) happy path test cases that should be tested (not test code). "
    "Arrange these test cases from the most important to the least important. "
    "Once you've created and arranged the test cases, share them with another agent called codia. ",
    agents="codia",
)

happy_pather = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    use_history=False,
    # use_tool=False,
    output_schema=HappyPaths.model_json_schema(),
    prompt_template=happy_pather_prompt_template,
    config={"retry": 3},
)

# Edge Caser Agent
edge_caser_prompt_template = get_base_prompt_template(
    name="edge_caser aka testers",
    custom_instructions="Your role is to generate and list (Just 10) edge test cases that should be tested (not test code). "
    "Arrange these test cases from the most important to the least important. "
    "Once you've created and arranged the test cases, share them with another agent called codia. ",
    agents="codia",
)


edge_caser = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    use_history=False,
    # use_tool=False,
    output_schema=EdgeCases.model_json_schema(),
    prompt_template=edge_caser_prompt_template,
    config={"retry": 3},
)


# Issue Finder Agent
issue_finder_prompt_template = get_base_prompt_template(
    name="issue_finder",
    custom_instructions="Your role is to identify and list issues with the provided code. "
    "Once you've identified the issues, share them with another agent called issue_verify. "
    "If the assistant failed to mention the installation of an external library that is used within the code , also include that in the issues",
    agents="issue_verify",
)

issue_finder = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    use_history=False,
    # use_tool=False,
    output_schema=Issues.model_json_schema(),
    prompt_template=issue_finder_prompt_template,
    config={"retry": 3},
)


# TURN CLASSIFICATION
turn_classifier_prompt_template = get_base_prompt_template(
    name="turn_classifier",
    custom_instructions="Your task is to examine the given message and determine if it contains executable code. "
    "Extract the complete code within the conversation without making any changes to the code itself, then classify the code "
    "if there are syntax error, report it as can not be tested and the reason why it can't as well"
    "If the code is complete and can be executed, please report this. If there is no code present in the response, ensure to report this as well. Do not create any code, only report on the code present in the message.",
    agents="testers",
)


turn_classifier = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    config={
        "params": {
            "temperature": 0.1,
        },
        "retry": 3,
    },
    use_history=False,
    name="turn",
    output_schema=TurnClassification.model_json_schema(),
    prompt_template=turn_classifier_prompt_template,
)


# TURN CLASSIFICATION 2 (NO CORRECTION)
turn_classifier_prompt_template2 = get_base_prompt_template(
    name="turn_classifier",
    custom_instructions="Your task is to examine the given messages  and determine if it contains executable code. "
    "if there are syntax error, report it as can not be tested and the reason why it can't as well"
    "If the code is complete and can be executed, please report this. If there is no code present in the response, ensure to report this as well. Do not create any code, only report on the code present in the messages.",
    agents="testers",
)


turn_classifier2 = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    config={
        "params": {
            "temperature": 0.1,
        },
        "retry": 3,
    },
    use_history=False,
    name="turn",
    output_schema=TurnClassificationNoCorrections.model_json_schema(),
    prompt_template=turn_classifier_prompt_template,
)


# FINAL EVALUATOR MERGER
chat_template = ChatPromptTemplate.from_messages(
    [("system", "{main_prompt}"), MessagesPlaceholder(variable_name="messages")]
)

chat_template = chat_template.partial(main_prompt=main_prompt)

evaluator = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    use_tool=True,
    use_history=False,
    output_schema=NotebookWiseFeedback.model_json_schema(),
    prompt_template=chat_template,
    config={"retry": 3},
)


# TURN MERGER

prompt_template_for_turn_merger = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are tasked with testing the code provided by the AI assistant turn by turn. "
            "To accomplish this, you will need to identify dependencies between the turns. "
            "For example, if the code in turn 3 depends on turn 1, you should list this dependency as [1, 3],"
            "An example is when a function, class, variable or imports are defined in another turn eg turn 1, and another turn (turn 2) needs this to run successfully then dependencies will be [1,2]. \n "
            "the list must be arranged accordingly and should end with the turn being analysed"
            "indicating that to test the code in turn 3, the code in turn 1 must be run first.\n\n"
            "if a turn need does not depend on any other turn then only the turn number should be in the list."
            "ALWAYS CALL AT LEAST AND AT MOST ONE TOOL. USE ONLY ONE TOOL PER CALL!\n"
            "YOUR OUTPUT MUST BE IN JSON FORMAT!\n"
            "ALL FIELDS IN THE CHOSEN TOOL MUST ALWAYS BE PROVIDED!\n"
            "PAY ATTENTION TO COMMAS AFTER EACH JSON VALUE WHERE NEEDED!",
        )
    ]
)


turn_merger = lambda: LLMModel(
    provider="openai_api",
    model="gpt-4o",
    use_history=False,
    # use_tool=False,
    output_schema=CodeDependencyList.model_json_schema(),
    prompt_template=prompt_template_for_turn_merger,
    config={"retry": 3},
)
