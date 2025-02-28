from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from llm_failover import ChatFailoverLLM


class LLMCellRoleFixer:
    def __init__(self, user="User", assistant="Assistant"):
        self.user = user
        self.assistant = assistant

    def predict_role(self, messages_subsequence):
        try:
            # Create a prompt template with system and user messages
            chat_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(
                        content=f"Your task is to accurately predict whether the empty role is a {self.user} or an {self.assistant}. You are only allowed to reply with a single word: '{self.user}' or '{self.assistant}'."
                    ),
                    HumanMessage(
                        content=f"Here's a part of the conversation including an empty role:\n\n{messages_subsequence}"
                    ),
                ]
            )

            # Initialize the LLM
            model = ChatFailoverLLM(
                initial_provider="openai_api",
                initial_model="gpt-4-turbo",
                temperature=0,
                max_tokens=4000,
                seed=42,
                streaming=True,
                callbacks=[],
            )

            # Execute the model with the prompt
            chain = chat_template | model | StrOutputParser()
            result = chain.invoke({})

            # Extract the missing role from the result
            print(result)
            missing_role = result.strip()
            print("Filling out missing role...")
            if missing_role not in [self.user, self.assistant]:
                raise Exception(
                    f"LLM output is not in the expected format for role fix: {missing_role} but expected one of {[self.user, self.assistant]}"
                )
            return missing_role, None
        except Exception as e:
            print(f"Error in fixing role: {e.__class__.__name__}: {str(e)}")
            return None, e

    def fix_missing_roles(self, messages):
        """
        Fix missing roles in a list of messages.

        :param messages: The list of messages.
        """
        errors = []
        for i in range(len(messages)):
            if messages[i]["role"] == "":
                subsequence = messages[max(0, i - 2) : min(len(messages), i + 3)]
                messages[i]["role"], error = self.predict_role(subsequence)
                if error is not None:
                    errors.append(error)
        return messages, errors
