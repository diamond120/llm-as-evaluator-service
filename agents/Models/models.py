import copy
import json
import os
import uuid
from abc import abstractmethod
from typing import Any

import tiktoken
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain.prompts.base import BasePromptTemplate
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from llm_failover import ChatFailoverLLM
from .schemas import (
    AspectorEvaluatorInputSchema,
    AspectorRole,
    FeedbackBasic,
    FeedbackISC,
    QualityAspect,
)


openai_encoding = tiktoken.get_encoding("cl100k_base")

import traceback
import inspect

def print_call_stack():
    # Get the current stack trace
    stack = inspect.stack()
    
    print("Call stack (most recent call last):")
    for frame in stack:
        print(f"Function: {frame.function} in {frame.filename}:{frame.lineno}")

def num_tokens_from_string(obj: Any) -> int:
    """Returns the number of tokens in a text string."""
    num_tokens = len(openai_encoding.encode(str(obj)))
    return num_tokens


def process_messages(messages, provider, model):
    if (
        provider == "openai_api"
        or model + provider == "llama-v3-70b-instruct" + "fireworks_api"
    ):
        print("DEBUG:", "...API token count")
        current_input = ""
        inputs = []
        outputs = []
        input_token = 0
        output_token = 0

        for message in messages:
            if isinstance(message, AIMessage):
                input_token += message.response_metadata["token_usage"]["prompt_tokens"]
                output_token += message.response_metadata["token_usage"][
                    "completion_tokens"
                ]

                inputs.append(
                    current_input
                )  # Save the current state of input_accumulator before adding AI content
                outputs.append(message.content)
                # Reset current_input to include all previous messages for the next AI message
                current_input += message.content
            else:
                current_input += message.content

        all_messages_concat = {"in": inputs, "out": outputs}
        all_in = all_messages_concat["in"]
        all_out = all_messages_concat["out"]
        return {"in": input_token, "out": output_token}, all_messages_concat

    elif provider in ["anthropic_api"]:
        print("DEBUG:", "...API token count")
        current_input = ""
        inputs = []
        outputs = []
        input_token = 0
        output_token = 0

        for message in messages:
            if isinstance(message, AIMessage):
                input_token += message.response_metadata["usage"]["input_tokens"]
                output_token += message.response_metadata["usage"]["output_tokens"]

                inputs.append(
                    current_input
                )  # Save the current state of input_accumulator before adding AI content
                outputs.append(message.content)
                # Reset current_input to include all previous messages for the next AI message
                current_input += message.content
            else:
                current_input += message.content

        all_messages_concat = {"in": inputs, "out": outputs}
        all_in = all_messages_concat["in"]
        all_out = all_messages_concat["out"]
        return {"in": input_token, "out": output_token}, all_messages_concat

    else:
        print("DEBUG:", "...Manual token count")
        current_input = ""
        inputs = []
        outputs = []

        for message in messages:
            if isinstance(message, AIMessage):
                inputs.append(
                    current_input
                )  # Save the current state of input_accumulator before adding AI content
                outputs.append(message.content)
                # Reset current_input to include all previous messages for the next AI message
                current_input += message.content
            else:
                current_input += message.content

        all_messages_concat = {"in": inputs, "out": outputs}
        all_in = all_messages_concat["in"]
        all_out = all_messages_concat["out"]
        return {
            "in": num_tokens_from_string("".join(all_in)),
            "out": num_tokens_from_string("".join(all_out)),
        }, all_messages_concat


def StructuredOutputParser(ai_message) -> dict:
    parsed = ai_message["parsed"]
    if isinstance(parsed, list):
        return parsed[0]["args"]
    return parsed


class LLMModel:
    def __init__(
        self,
        provider,
        model,
        config: dict = {},
        output_schema: dict = FeedbackBasic,
        input_schema=None,
        name: str = None,
        use_tool: bool = True,
        prompt_template: ChatPromptTemplate = None,
        try_to_parse: bool = True,
        chat_history: list = [],
        as_evaluator: bool = False,
        use_history: bool = True,
    ):

        self.output_type = None
        self.try_to_parse = try_to_parse
        self.test = False
        self.use_tool = use_tool
        self.provider = provider
        self.model = model
        self.config = config
        self.output_schema = output_schema
        self.input_schema = input_schema
        self.name = name
        self.as_evaluator = as_evaluator
        self.prompt_template = self.correct_prompt_template(prompt_template)
        self.chat_history = chat_history if chat_history else []
        self.chat_history_untouched = chat_history if chat_history else []
        self.id = str(uuid.uuid4())
        self.chain = None
        self.retry = self.config.get("retry", 3)
        self.retry_with_history = self.config.get("retry_with_history", False)
        self.use_history = use_history
        self.first_message = True
        self.initial_message = []

    def init(self):
        self.chain = self.create_chain()

    def __call__(self, messages, retrying=False):
        original_messages = copy.deepcopy(messages)

        if self.as_evaluator:
            # print(type(messages))
            if not isinstance(messages, self.input_schema):
                print("ERROR: INVALID SCHEMA")
                return None
            self.create_prompt_template(
                messages
            )  # use the instruction in the input to recreate the template
            messages = [HumanMessage(content=str(messages.conversation))]

        self.chain = self.create_chain()

        # here i check if you pass a dict
        if isinstance(messages, dict):
            # does it have messages in it?
            if "messages" in messages.keys():
                formated_message = self.prepare_messages(messages["messages"])
                messages.update(formated_message)
                IN_ = messages
            else:  # no messages just inputs, we add messages
                messages.update({"messages": []})
                IN_ = messages
        elif isinstance(messages, list):  # this  user pass a list of langchain messages
            IN_ = self.prepare_messages(messages)

        else:
            raise Exception("Wrong input format")

        # ----------

        if self.first_message == True:
            # print("INFO:", IN_)
            self.initial_message = self.prompt_template.invoke(IN_)
            self.first_message = False

        # ---------

        # if retrying:
        #     print("retrying params:")
        #     print(messages)
        #     print(IN_)
        #     print("retrying params end:")
        # if self.name == "turn":
        #     print("################################################################")
        #     print(IN_)
        #print_call_stack()
        response = self.chain.invoke(IN_)
        
        rx = self.add_to_history_and_prepare_response(response)

        # print("DEBUG: ", rx)
        if self.output_schema:
            return StructuredOutputParser(rx)
        return rx if isinstance(rx, str) else rx.content

    def validate_output_schema(self, output):
        if not isinstance(self.output_schema, dict) and self.try_to_parse:
            print("Validating output schema.....")
            self.output_schema.model_validate(output)

    def get_chat_history(self):
        return self.initial_message.messages + self.chat_history_untouched[1:]

    def create_chain(self):
        
        # GET LLM
        llm = self.create_model()

        # FORMAT INSTRUCTIONS
        if self.output_schema:
            llm.with_structured_output(self.output_schema, include_raw=True)
        
        # CHAIN CREATE
        return self.prompt_template | llm

    def prepare_messages(self, messages: list):

        self.chat_history.extend(messages)
        self.chat_history_untouched.extend(messages)

        # Convert to model specific format
        if self.provider in ["openai_api", "anthropic_api"]:
            return {"messages": self.chat_history}

        elif self.provider in ["fireworks_api"]:  # uses dict messages
            new_messages = []
            for message in self.chat_history:
                if isinstance(message, HumanMessage):
                    new_messages.append({"content": message.content, "role": "user"})
                elif isinstance(message, AIMessage):
                    new_messages.append(
                        {"content": message.content, "role": "assistant"}
                    )
                elif isinstance(message, SystemMessage):
                    new_messages.append({"content": message.content, "role": "system"})

                elif isinstance(message, FunctionMessage):
                    new_messages.append(
                        {"content": message.content, "role": "function"}
                    )

            return {"messages": new_messages}

    def add_to_history_and_prepare_response(self, response):
        # ensure response is an AImessage
        if isinstance(response, str):
            response = AIMessage(content=str(response))
        elif isinstance(response, dict) and "content" in response.keys():  # fireworks
            response = AIMessage(content=response["content"])
        # get response
        if self.use_history == True:
            self.chat_history.append(response)
            self.chat_history_untouched.append(response)
        else:
            self.chat_history = []  # clear the history if not to be saved
            self.chat_history_untouched = []
        return response

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider}, model={self.model}, name={self.name}-{self.id})"

    def create_model(self):
        return ChatFailoverLLM(
            initial_provider=self.provider,
            initial_model=self.model,
            **self.config.get("params", {}),
            streaming=False,
            model_kwargs=self.config.get("model_kwargs", {}),
        )

    def get_total_tokens(self):
        return process_messages(self.get_chat_history(), self.provider, self.model)

    def correct_prompt_template(self, old_prompt_template):
        new_prompt_template = copy.deepcopy(old_prompt_template)
        # if no prompt_template is given
        if not new_prompt_template:
            return ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        ""
                    ),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

        # add messages placeholder if nt already exists
        msg_pl_bool = [
            isinstance(msg_type, MessagesPlaceholder)
            for msg_type in new_prompt_template
        ]
        if msg_pl_bool:
            # verify that the variable name is messages
            for msg in new_prompt_template.messages:
                if isinstance(msg, MessagesPlaceholder):
                    if msg.variable_name == "messages":
                        return new_prompt_template
            new_prompt_template.append(MessagesPlaceholder(variable_name="messages"))
        else:
            new_prompt_template.append(MessagesPlaceholder(variable_name="messages"))

        return new_prompt_template

    def create_prompt_template(self, eval):
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a world class Evaluator, whose job is to evaluate the quality of the given aspect(s):\n{aspect}.\n\n"
                    "You are to focus on only the  responses from {role} in the conversation. i.e it is crucial that you evaluate the {role} messages/responses only.\n\n"
                    "Think step by step to figure out the correct evaluation(s) and provide you final response in this given format:\n"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        self.prompt_template = self.prompt_template.partial(aspect=eval.quality_aspect)
        self.prompt_template = self.prompt_template.partial(role=eval.role.value)

    def evaluate(self, evaluation_input):
        self.create_prompt_template(evaluation_input)
        task = [HumanMessage(content=str(evaluation_input.conversation))]
        result = self(task)
        return result.content
    