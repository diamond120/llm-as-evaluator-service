import os
from dotenv import load_dotenv

load_dotenv()

RUNS_BASE_PREFIX = "/api/v1/runs"

PENDING = "pending"
PROMPT = "prompt"
RUN_NOT_FOUND = "Run not found"
ADMIN = "admin"
ENGAGEMENT_DESCRIPTION = "A General  public engagement"
ENGAGEMENT_NAME = "public-engagement"

TEST_EMAIL = "test@example.com"

ACCESS_TOKEN = "ABCD123"

SQLITE_ASYNC_TEST_DATABASE = "sqlite+aiosqlite:///:memory:"


HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
}

NOT_AUTHENTICATED = "Not authenticated"
USER_NOT_AUTHORIZED = "User is not authorized."

MOCK_JWT_USER = {
    "user_email": TEST_EMAIL,
    "user_id": 1,
    "env": "DEVELOPMENT",
    "sub": "test@example.com",
    "exp": 1735689600,  # Set this to a future timestamp
}

BATCH_RUN_REQUEST = {
    "batch_name": "MetaTestRequest",
    "engagement_name": "public-engagement",
    "project_name": "prompt",
    "item_metadata": {},
    "input_type": "parsed_json_args",
    "aggregated_evaluations": [],
    "parse": True,
    "format_to_issues_scores": False,
    "is_dev_request": False,
    "inputs": [
        {
            "previous_messages": [
                {
                    "role": "user",
                    "content": 'I want\nto handle properly the user sesion\nin express \nso the user will enter\ninto app only\nif the browser has the session\nso I will need to set\nthe session\nthen I will need to be able\nto read\nwhich user is it by checking the session\ncould you please\nimplement two endpoints\none for generating the \nsession called login it will use sequelize\nfor matching user and password\nthen another endpoi called "me"\nthat will return the username \naccording the session',
                }
            ],
            "last_ai_reply": {},
            "conversation_metadata": {
                "Domain": "Web Development",
                "Subtopic": "Session Management with express-session in NodeJS",
                "Taxonomy Type": "Conversational Coding (Multi-turn)",
                "Task Difficulty": "Medium",
                "L2 Taxonomy Type": "Multi-turn code generation & synthesis",
                "Prompt Structure": "Messy",
                "Conversation Length": "Medium (2-4 turns)",
                "Programming Language": "JavaScript",
            },
            "human_review": [],
            "user_prompt": {
                "role": "user",
                "content": 'I want\nto handle properly the user sesion\nin express \nso the user will enter\ninto app only\nif the browser has the session\nso I will need to set\nthe session\nthen I will need to be able\nto read\nwhich user is it by checking the session\ncould you please\nimplement two endpoints\none for generating the \nsession called login it will use sequelize\nfor matching user and password\nthen another endpoi called "me"\nthat will return the username \naccording the session',
            },
        }
    ],
    "evaluations": [
        {
            "evaluator_name": "meta_last_user_prompt_evaluator_ev_smartest",
            "name": "prompt__metadata__domain",
            "config": {
                "quality_dimension_name": "prompt__metadata__domain",
                "quality_guidelines": "Do the  tasks in this prompt match the requirements of the domain in the metadata , give a score between 0-100 for each user request in prompt and calculate an overall score for the prompt. score > 50 indicate better adherence to the metadata. Check only the domain in metadata, do not comment on any other aspect of the metadata. ",
                "quality_evaluation_rules": " Respond with Pass if the score is >=50, Fail otherwise.",
            },
        },
        {
            "evaluator_name": "meta_last_user_prompt_evaluator_ev_smartest",
            "name": "prompt__metadata__subtopic",
            "config": {
                "quality_dimension_name": "prompt__metadata__subtopic",
                "quality_guidelines": "Do the  tasks in this prompt match the requirements of the subtopic in the metadata at least partially. Give a score between 0-100. score > 50 indicate better adherence to the subtopic in metadata. Check only the subtopic in metadata, do not comment on any other aspect of the metadata.\n",
                "quality_evaluation_rules": "Respond with Pass if the score is >=50, Fail otherwise. ",
            },
        },
        {
            "evaluator_name": "meta_last_user_prompt_evaluator_ev_smartest",
            "name": "prompt__metadata__structure",
            "config": {
                "quality_dimension_name": "prompt__metadata__structure",
                "quality_guidelines": 'Does the prompt match the prompt structure mentioned in the metadata ?  Provide a score between 0-100 for Only the respective prompt structure type mentioned in the metadata ( Messy, Normal or Super-Structured) . \nA Score > 50 indicates better adherence to the prompt structure mentioned in metadata.  Check only the prompt structure in metadata, do not comment on any other aspect of the metadata.\n\nHere\'s how to judge the prompt structure :\n"Messy "-  Prompt contains multiple mistakes such as  typos, vague or confusing language, grammatical mistakes etc. (> 3)\n"Super Structured" - Follows various prompt engineering tips like adding sections in prompt, giving the bot an identity, goal, specific output format etc.\n"Normal" - Articulates the question normally, even if briefly, with very few mistakes (< 3)',
                "quality_evaluation_rules": " Respond with Pass if the score is >=50, Fail otherwise. ",
            },
        },
        {
            "evaluator_name": "meta_last_user_prompt_evaluator_ev_smartest",
            "name": "prompt__multiturn__consistency",
            "config": {
                "quality_dimension_name": "prompt__multiturn__consistency",
                "quality_guidelines": "Validate this check only for Prompts after Step 1. Are the  tasks in this prompt in alignment with and are a continuation from the previous prompts. Give a score between 0-100. Evaluate only the prompt in the current step, on the basis of the prompts in the previous steps, do not comment on any other aspect of the task.\n",
                "quality_evaluation_rules": "Respond with Pass if the score is >=50, Fail otherwise.",
            },
        },
    ],
}

MOCK_CELERY_RESULT = [
    {
        "run_fields": {"stage1_failed": 1, "stage2_failed": 2, "status": "pending"},
        "run": {"run_id": 1, "status": "pending"},
        "evaluations": [
            {
                "evaluator_id": 1,
                "name": "Evaluation 1",
                "status": "success",
                "fail_reason": None,
                "output": {"Output 1": "output"},
                "is_used_for_aggregation": True,
                "is_aggregator": False,
            },
            {
                "evaluator_id": 2,
                "name": "Evaluation 2",
                "status": "failed",
                "fail_reason": "Error in processing",
                "output": None,
                "is_used_for_aggregation": False,
                "is_aggregator": False,
            },
            {
                "evaluator_id": 3,
                "name": "Evaluation 3",
                "status": "success",
                "fail_reason": None,
                "output": {"Output 3": "output"},
                "is_used_for_aggregation": True,
                "is_aggregator": True,
            },
        ],
    }
]
