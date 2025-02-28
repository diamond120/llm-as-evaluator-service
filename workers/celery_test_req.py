import os

import requests
from dotenv import load_dotenv

from app.db_api.models import User
from app.pydantic_models import BatchRunRequest, EvaluationRequest
from workers.celery_app import celery_app
from workers.slim_tasks import process_run

load_dotenv(override=True)


auth_headers = {"Authorization": f'Bearer {os.getenv("LLM_AS_EVALUATOR_API_KEY")}'}
payload = {
    "batch_name": "celery-testing",
    "engagement_name": "public-engagement",
    "project_name": "beta-test",
    "item_metadata": {},
    "input_type": "parsed_json_args",
    "inputs": [
        {
            "status": "OK",
            "metadata": {
                "metadata": "# Metadata\n\n**Occupation Topics** - Data Visualization Developer > Intermediate Interview preparation - User asks AI help to take an Interview. AI takes an interview\n\n**Target Number of Turns (User + Assistant)** - 4-8\n\n**Use Case** - Anticipating interview questions on optimizing data visualization for large datasets.\n\n**Technical Topic** - Efficient data handling with Pandas and dynamic plotting with Plotly.\n\n**User Personality** - Curious, open-minded, and practical. The user is eager to explore new solutions, receptive to different approaches, and values techniques that have real-world applications.\n"
            },
            "conversation": [
                {
                    "cell_pos": 1,
                    "role": "User",
                    "content": "Hi, could you explain the difference between loc and iloc in Pandas? Provide scenarios where using one is more advantageous than the other.",
                    "type": "markdown",
                },
                {
                    "cell_pos": 2,
                    "role": "Assistant",
                    "content": "Sure, let me check..",
                    "type": "markdown",
                },
            ],
        },
    ],
    "evaluations": [
        {
            "evaluator_name": "bao_code_gpt-4o",
            "name": f"code1",
            "use_for_agg_layer": True,
            "config": {},
        },
        {
            "evaluator_name": "bao_code_gpt-4o",
            "name": f"code2",
            "use_for_agg_layer": False,
            "config": {},
        },
    ],
    "aggregated_evaluations": [
        {
            "evaluator_name": "ca_summarizer_gpt-4o",
            "name": f"summarizer",
            "use_for_agg_layer": False,
            "config": {},
        }
    ],  # TODO
    "parse": True,
    "format_to_issues_scores": False,
    "is_dev_request": False,
}

payload_no_agg = {
    "batch_name": "celery-testing-stress",
    "engagement_name": "public-engagement",
    "project_name": "beta-test",
    "item_metadata": {},
    "input_type": "parsed_json_args",
    "inputs": [
        {
            "status": "OK",
            "metadata": {
                "metadata": "# Metadata\n\n**Occupation Topics** - Data Visualization Developer > Intermediate Interview preparation - User asks AI help to take an Interview. AI takes an interview\n\n**Target Number of Turns (User + Assistant)** - 4-8\n\n**Use Case** - Anticipating interview questions on optimizing data visualization for large datasets.\n\n**Technical Topic** - Efficient data handling with Pandas and dynamic plotting with Plotly.\n\n**User Personality** - Curious, open-minded, and practical. The user is eager to explore new solutions, receptive to different approaches, and values techniques that have real-world applications.\n"
            },
            "conversation": [
                {
                    "cell_pos": 1,
                    "role": "User",
                    "content": "Hi, could you explain the difference between loc and iloc in Pandas? Provide scenarios where using one is more advantageous than the other.",
                    "type": "markdown",
                },
                {
                    "cell_pos": 2,
                    "role": "Assistant",
                    "content": "Sure, let me check..",
                    "type": "markdown",
                },
            ],
        },
    ],
    "evaluations": [
        {
            "evaluator_name": "bao_code_gpt-4o",
            "name": f"code1",
            "use_for_agg_layer": True,
            "config": {},
        },
        {
            "evaluator_name": "bao_code_gpt-4o",
            "name": f"code2",
            "use_for_agg_layer": False,
            "config": {},
        },
    ],
    "aggregated_evaluations": [],  # TODO
    "parse": True,
    "format_to_issues_scores": False,
    "is_dev_request": False,
}

dev_payload = {
    "batch_name": "celery-testing",
    "engagement_name": "public-engagement",
    "project_name": "beta-test",
    "item_metadata": {},
    "input_type": "parsed_json_args",
    "inputs": [
        {
            "status": "OK",
            "metadata": {
                "metadata": "# Metadata\n\n**Occupation Topics** - Data Visualization Developer > Intermediate Interview preparation - User asks AI help to take an Interview. AI takes an interview\n\n**Target Number of Turns (User + Assistant)** - 4-8\n\n**Use Case** - Anticipating interview questions on optimizing data visualization for large datasets.\n\n**Technical Topic** - Efficient data handling with Pandas and dynamic plotting with Plotly.\n\n**User Personality** - Curious, open-minded, and practical. The user is eager to explore new solutions, receptive to different approaches, and values techniques that have real-world applications.\n"
            },
            "conversation": [
                {
                    "cell_pos": 1,
                    "role": "User",
                    "content": "Hi, could you explain the difference between loc and iloc in Pandas? Provide scenarios where using one is more advantageous than the other.",
                    "type": "markdown",
                },
                {
                    "cell_pos": 2,
                    "role": "Assistant",
                    "content": "Sure, let me check..",
                    "type": "markdown",
                },
            ],
        },
    ],
    "evaluations": [
        {
            "evaluator_name": None,
            "name": "some_unique_name_inside_this_run1",
            "use_for_agg_layer": True,
            "config": {"review_topic": "movie"},
            "evaluator_config_override": {
                "evaluator_type_name": "single_stage_messages_evaluator",
                "name": "Some random name",
                "config": {
                    "messages": [
                        (
                            "system",
                            "Given this review, please provide its sentiment analysis. This review is about {review_topic}.\n\nREVIEW_START\n{review_content}\nREVIEW_END\n",
                        )
                    ]
                },
                "llm_config": {
                    "provider": "openai_api",
                    "model": "gpt-4o",
                    "params": {"temperature": 0, "seed": 42, "max_tokens": 4000},
                },
                "input_schema": {
                    "properties": {
                        "review_content": {"title": "Review Content"},
                        "review_topic": {"title": "Review Topic", "type": "string"},
                    },
                    "required": ["review_content", "review_topic"],
                    "title": "InputSchema",
                    "type": "object",
                },
                "output_schema": {
                    "description": "Sentiment analysis output",
                    "properties": {
                        "scratchpad": {
                            "description": "Place to think about the review",
                            "title": "Scratchpad",
                            "type": "string",
                        },
                        "probability_user_watched_the_movie": {
                            "description": "One of HIGH, LOW, UNCERTAIN",
                            "title": "Probability User Watched The Movie",
                            "type": "string",
                        },
                        "review_sentiment": {
                            "description": "Sentiment of the review, e.g., positive, negative, neutral",
                            "title": "Review Sentiment",
                            "type": "string",
                        },
                    },
                    "required": [
                        "scratchpad",
                        "probability_user_watched_the_movie",
                        "review_sentiment",
                    ],
                    "title": "SentimentAnalysisOutput",
                    "type": "object",
                },
            },
        },
        {
            "evaluator_name": None,
            "name": "some_unique_name_inside_this_run2",
            "use_for_agg_layer": True,
            "config": {"review_topic": "movie"},
            "evaluator_config_override": {
                "evaluator_type_name": "single_stage_messages_evaluator",
                "name": "Some random name",
                "config": {
                    "messages": [
                        (
                            "system",
                            "Given this review, please provide its sentiment analysis. This review is about {review_topic}.\n\nREVIEW_START\n{review_content}\nREVIEW_END\n",
                        )
                    ]
                },
                "llm_config": {
                    "provider": "openai_api",
                    "model": "gpt-4o",
                    "params": {"temperature": 0, "seed": 42, "max_tokens": 4000},
                },
                "input_schema": {
                    "properties": {
                        "review_content": {"title": "Review Content"},
                        "review_topic": {"title": "Review Topic", "type": "string"},
                    },
                    "required": ["review_content", "review_topic"],
                    "title": "InputSchema",
                    "type": "object",
                },
                "output_schema": {
                    "description": "Sentiment analysis output",
                    "properties": {
                        "scratchpad": {
                            "description": "Place to think about the review",
                            "title": "Scratchpad",
                            "type": "string",
                        },
                        "probability_user_watched_the_movie": {
                            "description": "One of HIGH, LOW, UNCERTAIN",
                            "title": "Probability User Watched The Movie",
                            "type": "string",
                        },
                        "review_sentiment": {
                            "description": "Sentiment of the review, e.g., positive, negative, neutral",
                            "title": "Review Sentiment",
                            "type": "string",
                        },
                    },
                    "required": [
                        "scratchpad",
                        "probability_user_watched_the_movie",
                        "review_sentiment",
                    ],
                    "title": "SentimentAnalysisOutput",
                    "type": "object",
                },
            },
        },
    ],
    "aggregated_evaluations": [
        {
            "evaluator_name": "ca_summarizer_gpt-4o",
            "name": f"summarizer",
            "use_for_agg_layer": False,
            "config": {},
        }
    ],  # TODO
    "parse": True,
    "format_to_issues_scores": False,
    "is_dev_request": True,
}

dev_payload_plus_agg_dev = {
    "batch_name": "celery-testing",
    "engagement_name": "public-engagement",
    "project_name": "beta-test",
    "item_metadata": {},
    "input_type": "parsed_json_args",
    "inputs": [
        {
            "status": "OK",
            "metadata": {
                "metadata": "# Metadata\n\n**Occupation Topics** - Data Visualization Developer > Intermediate Interview preparation - User asks AI help to take an Interview. AI takes an interview\n\n**Target Number of Turns (User + Assistant)** - 4-8\n\n**Use Case** - Anticipating interview questions on optimizing data visualization for large datasets.\n\n**Technical Topic** - Efficient data handling with Pandas and dynamic plotting with Plotly.\n\n**User Personality** - Curious, open-minded, and practical. The user is eager to explore new solutions, receptive to different approaches, and values techniques that have real-world applications.\n"
            },
            "conversation": [
                {
                    "cell_pos": 1,
                    "role": "User",
                    "content": "Hi, could you explain the difference between loc and iloc in Pandas? Provide scenarios where using one is more advantageous than the other.",
                    "type": "markdown",
                },
                {
                    "cell_pos": 2,
                    "role": "Assistant",
                    "content": "Sure, let me check..",
                    "type": "markdown",
                },
            ],
        },
    ],
    "evaluations": [
        {
            "evaluator_name": None,
            "name": "some_unique_name_inside_this_run1",
            "use_for_agg_layer": True,
            "config": {"review_topic": "movie"},
            "evaluator_config_override": {
                "evaluator_type_name": "single_stage_messages_evaluator",
                "name": "Some random name",
                "config": {
                    "messages": [
                        (
                            "system",
                            "Given this review, please provide its sentiment analysis. This review is about {review_topic}.\n\nREVIEW_START\n{review_content}\nREVIEW_END\n",
                        )
                    ]
                },
                "llm_config": {
                    "provider": "openai_api",
                    "model": "gpt-4o",
                    "params": {"temperature": 0, "seed": 42, "max_tokens": 4000},
                },
                "input_schema": {
                    "properties": {
                        "review_content": {"title": "Review Content"},
                        "review_topic": {"title": "Review Topic", "type": "string"},
                    },
                    "required": ["review_content", "review_topic"],
                    "title": "InputSchema",
                    "type": "object",
                },
                "output_schema": {
                    "description": "Sentiment analysis output",
                    "properties": {
                        "scratchpad": {
                            "description": "Place to think about the review",
                            "title": "Scratchpad",
                            "type": "string",
                        },
                        "probability_user_watched_the_movie": {
                            "description": "One of HIGH, LOW, UNCERTAIN",
                            "title": "Probability User Watched The Movie",
                            "type": "string",
                        },
                        "review_sentiment": {
                            "description": "Sentiment of the review, e.g., positive, negative, neutral",
                            "title": "Review Sentiment",
                            "type": "string",
                        },
                    },
                    "required": [
                        "scratchpad",
                        "probability_user_watched_the_movie",
                        "review_sentiment",
                    ],
                    "title": "SentimentAnalysisOutput",
                    "type": "object",
                },
            },
        },
        {
            "evaluator_name": None,
            "name": "some_unique_name_inside_this_run2",
            "use_for_agg_layer": True,
            "config": {"review_topic": "movie"},
            "evaluator_config_override": {
                "evaluator_type_name": "single_stage_messages_evaluator",
                "name": "Some random name",
                "config": {
                    "messages": [
                        (
                            "system",
                            "Given this review, please provide its sentiment analysis. This review is about {review_topic}.\n\nREVIEW_START\n{review_content}\nREVIEW_END\n",
                        )
                    ]
                },
                "llm_config": {
                    "provider": "openai_api",
                    "model": "gpt-4o",
                    "params": {"temperature": 0, "seed": 42, "max_tokens": 4000},
                },
                "input_schema": {
                    "properties": {
                        "review_content": {"title": "Review Content"},
                        "review_topic": {"title": "Review Topic", "type": "string"},
                    },
                    "required": ["review_content", "review_topic"],
                    "title": "InputSchema",
                    "type": "object",
                },
                "output_schema": {
                    "description": "Sentiment analysis output",
                    "properties": {
                        "scratchpad": {
                            "description": "Place to think about the review",
                            "title": "Scratchpad",
                            "type": "string",
                        },
                        "probability_user_watched_the_movie": {
                            "description": "One of HIGH, LOW, UNCERTAIN",
                            "title": "Probability User Watched The Movie",
                            "type": "string",
                        },
                        "review_sentiment": {
                            "description": "Sentiment of the review, e.g., positive, negative, neutral",
                            "title": "Review Sentiment",
                            "type": "string",
                        },
                    },
                    "required": [
                        "scratchpad",
                        "probability_user_watched_the_movie",
                        "review_sentiment",
                    ],
                    "title": "SentimentAnalysisOutput",
                    "type": "object",
                },
            },
        },
    ],
    "aggregated_evaluations": [
        {
            "evaluator_name": None,
            "name": "some_unique_name_inside_this_run3_agg",
            "use_for_agg_layer": True,
            "config": {"review_topic": "movie"},
            "evaluator_config_override": {
                "evaluator_type_name": "single_stage_system_prompt",
                "name": "Some random name",
                "config": {
                    "messages": [
                        (
                            "system",
                            "Given this review, please provide its sentiment analysis. This review is about {review_topic}.\n\nREVIEW_START\n{review_content}\nREVIEW_END\n",
                        )
                    ]
                },
                "llm_config": {
                    "provider": "openai_api",
                    "model": "gpt-4o",
                    "params": {"temperature": 0, "seed": 42, "max_tokens": 4000},
                },
                "input_schema": {
                    "properties": {
                        "review_content": {"title": "Review Content"},
                        "review_topic": {"title": "Review Topic", "type": "string"},
                    },
                    "required": ["review_content", "review_topic"],
                    "title": "InputSchema",
                    "type": "object",
                },
                "output_schema": {
                    "description": "Sentiment analysis output",
                    "properties": {
                        "scratchpad": {
                            "description": "Place to think about the review",
                            "title": "Scratchpad",
                            "type": "string",
                        },
                        "probability_user_watched_the_movie": {
                            "description": "One of HIGH, LOW, UNCERTAIN",
                            "title": "Probability User Watched The Movie",
                            "type": "string",
                        },
                        "review_sentiment": {
                            "description": "Sentiment of the review, e.g., positive, negative, neutral",
                            "title": "Review Sentiment",
                            "type": "string",
                        },
                    },
                    "required": [
                        "scratchpad",
                        "probability_user_watched_the_movie",
                        "review_sentiment",
                    ],
                    "title": "SentimentAnalysisOutput",
                    "type": "object",
                },
            },
        },
    ],  # TODO
    "parse": True,
    "format_to_issues_scores": False,
    "is_dev_request": True,
}
import time

dev_payload_partials_all_and_mix = {
    "batch_name": "celery-testing",
    "engagement_name": "public-engagement",
    "project_name": "beta-test",
    "item_metadata": {},
    "input_type": "parsed_json_args",
    "inputs": [
        {
            "status": "OK",
            "metadata": {
                "metadata": "# Metadata\n\n**Occupation Topics** - Data Visualization Developer > Intermediate Interview preparation - User asks AI help to take an Interview. AI takes an interview\n\n**Target Number of Turns (User + Assistant)** - 4-8\n\n**Use Case** - Anticipating interview questions on optimizing data visualization for large datasets.\n\n**Technical Topic** - Efficient data handling with Pandas and dynamic plotting with Plotly.\n\n**User Personality** - Curious, open-minded, and practical. The user is eager to explore new solutions, receptive to different approaches, and values techniques that have real-world applications.\n"
            },
            "conversation": [
                {
                    "cell_pos": 1,
                    "role": "User",
                    "content": "Hi, could you explain the difference between loc and iloc in Pandas? Provide scenarios where using one is more advantageous than the other.",
                    "type": "markdown",
                },
                {
                    "cell_pos": 2,
                    "role": "Assistant",
                    "content": "Sure, let me check..",
                    "type": "markdown",
                },
            ],
        },
    ],
    "evaluations": [
        {
            "evaluator_name": "bao_code_gpt-4o",
            "name": "some_unique_name_inside_this_run1",
            "use_for_agg_layer": True,
            "config": {"quality_aspect": "How good was AI reply?", "role": "llm"},
            "evaluator_config_override": {
                "output_schema": {
                    "description": "Improved aspect review output.",
                    "properties": {
                        "plan_steps": {
                            "description": "Outline steps to do the review. e.g. To do this I will do thing A that involves writing such and such.",
                            "title": "Plan Steps",
                            "type": "string",
                        },
                        "steps_execution": {
                            "description": "Follow the steps here and do the review in this field. e.g. Thing A: write the actual reasoning thoughts here, step by step reasoning with answers.",
                            "title": "Steps Execution",
                            "type": "string",
                        },
                        "issues": {
                            "description": "A concrete list of issues in the conversation. 15 words or less each.",
                            "items": {"type": "string"},
                            "title": "Issues",
                            "type": "array",
                        },
                        "score": {
                            "description": "A score representing how good the conversation is in the given quality aspect, 1 is terrible, 5 is exemplary and flawless.",
                            "maximum": 5,
                            "minimum": 1,
                            "title": "Score",
                            "type": "integer",
                        },
                    },
                    "required": ["plan_steps", "steps_execution", "issues", "score"],
                    "title": "AspectReview",
                    "type": "object",
                }
            },
        },
        {
            "evaluator_name": "ca_aspector_gpt-4o",
            "name": "some_unique_name_inside_this_run2",
            "use_for_agg_layer": True,
            "config": {"quality_aspect": "How good was AI reply?", "role": "llm"},
            "evaluator_config_override": {
                "output_schema": {
                    "description": "Improved aspect review output.",
                    "properties": {
                        "plan_steps": {
                            "description": "Outline steps to do the review. e.g. To do this I will do thing A that involves writing such and such.",
                            "title": "Plan Steps",
                            "type": "string",
                        },
                        "steps_execution": {
                            "description": "Follow the steps here and do the review in this field. e.g. Thing A: write the actual reasoning thoughts here, step by step reasoning with answers.",
                            "title": "Steps Execution",
                            "type": "string",
                        },
                        "issues": {
                            "description": "A concrete list of issues in the conversation. 15 words or less each.",
                            "items": {"type": "string"},
                            "title": "Issues",
                            "type": "array",
                        },
                        "score": {
                            "description": "A score representing how good the conversation is in the given quality aspect, 1 is terrible, 5 is exemplary and flawless.",
                            "maximum": 5,
                            "minimum": 1,
                            "title": "Score",
                            "type": "integer",
                        },
                    },
                    "required": ["plan_steps", "steps_execution", "issues", "score"],
                    "title": "AspectReview",
                    "type": "object",
                }
            },
        },
        {
            "evaluator_name": "bao_code_gpt-4o",
            "name": f"code2",
            "use_for_agg_layer": False,
            "config": {},
        },
    ],
    "aggregated_evaluations": [
        {
            "evaluator_name": "ca_summarizer_gpt-4o",
            "name": "some_unique_name_inside_this_run_agg",
            "use_for_agg_layer": True,
            "config": {"quality_aspect": "How good was AI reply?", "role": "llm"},
            "evaluator_config_override": {
                "output_schema": {
                    "description": "Improved aspect review output.",
                    "properties": {
                        "plan_steps": {
                            "description": "Outline steps to do the review. e.g. To do this I will do thing A that involves writing such and such.",
                            "title": "Plan Steps",
                            "type": "string",
                        },
                        "steps_execution": {
                            "description": "Follow the steps here and do the review in this field. e.g. Thing A: write the actual reasoning thoughts here, step by step reasoning with answers.",
                            "title": "Steps Execution",
                            "type": "string",
                        },
                        "issues": {
                            "description": "A concrete list of issues in the conversation. 15 words or less each.",
                            "items": {"type": "string"},
                            "title": "Issues",
                            "type": "array",
                        },
                        "score": {
                            "description": "A score representing how good the conversation is in the given quality aspect, 1 is terrible, 5 is exemplary and flawless.",
                            "maximum": 5,
                            "minimum": 1,
                            "title": "Score",
                            "type": "integer",
                        },
                    },
                    "required": ["plan_steps", "steps_execution", "issues", "score"],
                    "title": "AspectReview",
                    "type": "object",
                }
            },
        },
    ],  # TODO
    "parse": True,
    "format_to_issues_scores": False,
    "is_dev_request": False,
}


def test_process_run():
    # Create a dummy request
    print("START REQUEST TIME", time.time())
    r = requests.post(
        "http://127.0.0.1:8887/api/v1/slim_runs/",
        headers=auth_headers,
        json=payload_no_agg,
    )
    print(r.status_code, r.text)


from concurrent.futures import ThreadPoolExecutor


def run_test_process_in_parallel(times: int):
    with ThreadPoolExecutor(max_workers=1000) as executor:
        futures = [executor.submit(test_process_run) for _ in range(times)]
        for future in futures:
            future.result()


run_test_process_in_parallel(1)

# celery -A workers.celery_worker worker -Q process_queue -P gevent -n process_worker@%h -l debug -E
