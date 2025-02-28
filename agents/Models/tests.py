

from Models.models import LLMModel
import pytest
from langchain.prompts import HumanMessagePromptTemplate
from langchain_core.messages import (HumanMessage)
from langchain.prompts import SystemMessagePromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field, validator
import json
from Models.schemas import NotebookWiseFeedback



#----------------------------------------------------------------
class Joke(BaseModel):
    """Joke model"""
    SETUP: str = Field(..., description="setup for the joke")
    PUNCHLINE: str = Field(..., description="punchline for the joke")


prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Given this topic={topic}, generate a joke."
                ),
                (
                    "human",
                    "Also, make your output all upper case LIKE THIS."
                )
               
            ]
        )






conversation = {'status': 'OK',
 'metadata': {'metadata': '# Metadata\n\n**Python Topics** - algorithms > by_topic > probability\n\n**Type** - query\n\n**Target Number of Turns (User + Assistant)** - 2\n'},
 'conversation': [{'cell_pos': 1,
   'role': 'User',
   'content': 'Could you show me a Python function to calculate the probability of rolling a sum of 8 with two six-sided dice?',
   'type': 'markdown'},
  {'cell_pos': 2,
   'role': 'Assistant',
   'content': 'Certainly! When you roll two six-sided dice, there are 36 possible outcomes (as there are 6 possible outcomes for each die). To determine the probability of obtaining a sum of 8, you must identify the favorable outcomes (those resulting in a sum of 8) and then divide this count by the total number of possible outcomes.\n\nHere is a python function for it:',
   'type': 'markdown'},
  {'cell_pos': 3,
   'role': 'Assistant',
   'content': 'def probability_of_rolling_sum_eight():\n    favorable_outcomes = 0\n    total_outcomes = 36 # There are 6 * 6 = 36 total outcomes\n\n    for dice_1 in range(1, 7):\n        dice_2 = 8 - dice_1\n\n        # Check if the value is valid\n        if 1 <= dice_2 <= 6:\n            favorable_outcomes += 1\n\n    return favorable_outcomes / total_outcomes\n\n# Call the function and print the result\nprobability_of_rolling_sum_eight = probability_of_rolling_sum_eight()\n\nprint(f"The probability of rolling a sum of 8 with two six-sided dice is: {probability_of_rolling_sum_eight}")',
   'type': 'code'},
  {'cell_pos': 4,
   'role': 'Assistant',
   'content': 'The time complexity of the `probability_of_rolling_sum_eight` function is O(N) since it undergoes a constant number of iterations (6 iterations, corresponding to each possible value of dice_1 ranging from 1 to 6).The loop entails basic arithmetic operations and conditional checks, all with constant time complexity.\n\nAs a result, the time complexity remains constant and is not influenced by the input size, irrespective of the number of sides on the dice. The function is specifically tailored for six-sided dice, ensuring a consistent and limited number of iterations.',
   'type': 'markdown'},
  {'cell_pos': 5,
   'role': 'User',
   'content': 'Could you kindly provide the result with precision up to four decimal places only?',
   'type': 'markdown'},
  {'cell_pos': 6,
   'role': 'Assistant',
   'content': "Certainly! Here's the revised version of the function that will provide the outcome with accuracy up to four decimal places.",
   'type': 'markdown'},
  {'cell_pos': 7,
   'role': 'Assistant',
   'content': 'def probability_of_rolling_sum_eight():\n    favorable_outcomes = 0\n    total_outcomes = 36 # There are 6 * 6 = 36 total outcomes\n\n    for die1 in range(1, 7):\n        die2 = 8 - die1\n\n        # Check if the value is valid\n        if 1 <= die2 <= 6:\n            favorable_outcomes += 1\n\n    return favorable_outcomes / total_outcomes\n\n# Call the function and print the result\nprobability_of_rolling_sum_eight = probability_of_rolling_sum_eight()\n\nprint(f"The probability of rolling a sum of 8 with two six-sided dice is: {probability_of_rolling_sum_eight: .4f}")',
   'type': 'code'}]}

chat_template = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                """Name: AI Assistant Perfector.
Profile: You are an expert in perfecting AI Assistants' response content based on the user's expertise level."""
            ),
            HumanMessagePromptTemplate.from_template(
                """
Given the following conversation between Human User and AI Assistant, find issues following the rules described below and rate the total conversation.
Single significant instance of deviation from the rules - score 1 or 2. More issues score<2. No issues=5.

Qualities we care about. Focus on them and only find issues that are directly related to them:
```
You must assume the user just started to learn about the question that is asked, so the 
reply should cover all the points that the user might be new to, and assume the 
user has basic knowledge about the prerequisites. 

This helps us keep the explanation clean, and makes it useful to the user rather 
than throwing all information about the topic to the user.

It is important to identify the query intent to gauge the user knowledge level as well as 
the code complexity to provide the most useful explanation.
```

The task:
```
Please, detect all mismatches between user's expertise level shown and the replies of the Assistant.
If User expertise level is unknown - asumme they are a beginner in that question.
Mismatches might include but not limited to:
    - too much explanation for an expert
    - too little explanation for a beginner
    - Assistant assumes the user is not the beginner in the question asked be it an algo or a technology or something else.

Assume basic knowledge of Python programming by the user and so no need to explain basic things unless asked to.
For example, if the question is about an algorithm in python, assume understnding of Python but a beginner level in algorithms UNLESS USER SHOWS OR STATES A HIGHER OR LOWER LEVEL OF EXPERTISE.

If no issues found, do not create any.
Correctness or accuracy is not your concern and will be handled by other evaluators. Focus only on the serving user's level of expertise in the most helpful manner.
```

Conversation:
CONVERSATION_START
{conversation}
CONVERSATION_END

Now, proceed to completing your task of finding issues and scoring the conversation.
"""
            ),
        ]
    )
#----------------------------------------------------------------





class TestLLMModel:

    # LLMModel can be initialized with the correct parameters without raising any exceptions
    def test_initialize_llm_model_without_exceptions(self):
        provider = "openai_api"
        model = "gpt-3.5-turbo"
        config = {}
        tools = []
        output_schema = None
        input_schema = None
        name = "LLM Model"
        prompt_template = None
        try_to_parse = True
        chat_history = []
        as_evaluator = False
        use_history = True

        try:
            llm_model = LLMModel(provider, model, config, tools, output_schema, input_schema, name, prompt_template, try_to_parse, chat_history, as_evaluator, use_history)
            assert isinstance(llm_model, LLMModel)
        except Exception as e:
            pytest.fail(str(e))

    # LLMModel can handle invalid input schemas and raise an exception
    def test_handle_invalid_input_schemas(self):
        provider = "openai_api"
        model = "gpt-3.5-turbo"
        config = {}
        tools = []
        output_schema = None
        input_schema = None
        name = "LLM Model"
        prompt_template = None
        try_to_parse = True
        chat_history = []
        as_evaluator = False
        use_history = True

        with pytest.raises(Exception):
            llm_model = LLMModel(provider, model, config, tools, output_schema, input_schema, name, prompt_template, try_to_parse, chat_history, as_evaluator, use_history)
            invalid_input = "Invalid input"
            llm_model(invalid_input)
            
            
            
            
    ##TEST ALL MODELS
        ##PYDANTIC AS OUTPUT SCHEMA
        
    def test_openai_models(self): 
        models = [
            "gpt-3.5-turbo-1106",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-4o",
        ]
        provider = "openai_api"
        print(f"Testing models from provider: {provider}")
        for model in models:
            print(f"Testing model: {model}")
            evaluator = LLMModel(
                provider=provider,
                model=model,
                output_schema=Joke.model_json_schema(),
                name="aspect_evaluator",
                prompt_template=prompt_template,
                try_to_parse=True,
                config={
                    "retry": 4,
                }
            )

            # Perform evaluation
            evaluation_result = evaluator({
                "topic": "dad_jokes"
            })

            Joke.model_validate(evaluation_result)


    # def test_anthropic_models(self):
    #     models = [
    #         "claude-3-opus-20240229",
    #     ]
    #     provider = "anthropic_api"
    #     print(f"Testing models from provider: {provider}")
    #     for model in models:
    #         print(f"Testing model: {model}")
    #         evaluator = LLMModel(
    #             provider=provider,
    #             model=model,
    #             output_schema=Joke.model_json_schema(),
    #             name="aspect_evaluator",
    #             prompt_template=prompt_template,
    #             try_to_parse=True,
    #             config={
    #                 "retry": 3,
                    
    #             }
    #         )

    #         # Perform evaluation
    #         evaluation_result = evaluator({
    #            "topic": "dad_jokes"
    #         })

    #         Joke.model_validate(evaluation_result)

    def test_fireworks_models(self):
        models = [
           "llama-v3-70b-instruct",
            "dbrx-instruct",
            "mixtral-8x22b-instruct",
             "llama-v3-8b-instruct"
        ]
        provider = "fireworks_api"
        print(f"Testing models from provider: {provider}")
        for model in models:
            print(f"Testing model: {model}")
            evaluator = LLMModel(
                provider=provider,
                model=model,
                output_schema=Joke.model_json_schema(),
                name="aspect_evaluator",
                prompt_template=prompt_template,
                try_to_parse=True,
                config={
                    "retry": 3,
                  
                }
            )

            # Perform evaluation
            evaluation_result = evaluator({
               "topic": "dad_jokes"
            })

            Joke.model_validate(evaluation_result)


        ## JSON AS OUTPUT SCHEMA
    def test_openai_models(self): 
            models = [
                "gpt-3.5-turbo-1106",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "gpt-4o",
            ]
            provider = "openai_api"
            print(f"Testing models from provider: {provider}")
            for model in models:
                print(f"Testing model: {model}")
                evaluator = LLMModel(
                    provider=provider,
                    model=model,
                    output_schema=Joke.model_json_schema(),
                    name="aspect_evaluator",
                    prompt_template=prompt_template,
                    try_to_parse=True,
                    config={
                        "retry": 4,
                    }
                )

                # Perform evaluation
                evaluation_result = evaluator({
                    "topic": "dad_jokes"
                })

                Joke.model_validate(evaluation_result)


    # def test_anthropic_models(self):
    #     models = [
    #         "claude-3-opus-20240229",
    #     ]
    #     provider = "anthropic_api"
    #     print(f"Testing models from provider: {provider}")
    #     for model in models:
    #         print(f"Testing model: {model}")
    #         evaluator = LLMModel(
    #             provider=provider,
    #             model=model,
    #             output_schema=Joke.model_json_schema(),
    #             name="aspect_evaluator",
    #             prompt_template=prompt_template,
    #             try_to_parse=True,
    #             config={
    #                 "retry": 3,
                    
    #             }
    #         )

    #         # Perform evaluation
    #         evaluation_result = evaluator({
    #            "topic": "dad_jokes"
    #         })

    #         Joke.model_validate(evaluation_result)

    def test_fireworks_models(self):
        models = [
        "llama-v3-70b-instruct",
            "dbrx-instruct",
            "mixtral-8x22b-instruct",
            "llama-v3-8b-instruct"
        ]
        provider = "fireworks_api"
        print(f"Testing models from provider: {provider}")
        for model in models:
            print(f"Testing model: {model}")
            evaluator = LLMModel(
                provider=provider,
                model=model,
                output_schema=Joke.model_json_schema(),
                name="aspect_evaluator",
                prompt_template=prompt_template,
                try_to_parse=True,
                config={
                    "retry": 3,
                
                }
            )

            # Perform evaluation
            evaluation_result = evaluator({
            "topic": "dad_jokes"
            })

            Joke.model_validate(evaluation_result)