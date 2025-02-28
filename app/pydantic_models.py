import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class RunStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_FAIL = "partial_fail"


class LLMConfig(BaseModel):
    provider: str
    model: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EvaluatorFromCopy(BaseModel):
    src_evaluator_name: str


class EvaluatorConfigOverride(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    llm_config: Optional[LLMConfig] = None
    output_schema: Optional[Dict[str, Any]] = Field(default_factory=dict)
    input_schema: Optional[Dict[str, Any]] = Field(default_factory=dict)
    evaluator_type_name: Optional[str] = None
    description: Optional[str] = None

    def to_db_model(self, evaluator_type_id: int):
        # Convert Pydantic model to SQLAlchemy model data dictionary
        return {
            "name": self.name,
            "evaluator_type_id": evaluator_type_id,
            "description": self.description or "No description provided.",
            "config": self.config,
            "llm_provider": self.llm_config.provider if self.llm_config else None,
            "llm_model": self.llm_config.model if self.llm_config else None,
            "llm_params": self.llm_config.params if self.llm_config else None,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


class EvaluationRequest(BaseModel):
    evaluator_name: Optional[str] = None
    evaluator_id: Optional[int] = None
    name: str
    is_aggregator: Optional[bool] = Field(default=False)
    use_for_agg_layer: Optional[bool] = Field(default=False)
    config: dict[str, Any]
    evaluator_config_override: Optional[EvaluatorConfigOverride] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.validate()

    def validate(self):
        if self.evaluator_config_override is None and not (
            self.evaluator_name or self.evaluator_id
        ):
            print(self.evaluator_config_override)
            raise ValueError("Either evaluator_name or evaluator_id must be provided")
        elif self.evaluator_name and self.evaluator_id:
            raise ValueError(
                "Both evaluator_name and evaluator_id cannot be provided together"
            )

    @classmethod
    def from_no_evaluator(cls, no_eval_request, evaluator_id):
        return cls(**{**no_eval_request.dict(), "evaluator_id": evaluator_id})


class EvaluationRequestNoEvaluator(EvaluationRequest):

    def validate(self):
        if self.evaluator_name is not None or self.evaluator_id is not None:
            raise ValueError(
                "Evaluator name or ID should not be provided for EvaluationRequestNoEvaluator"
            )


class BatchRunRequest(BaseModel):
    batch_name: str
    engagement_name: Optional[str] = None
    project_name: Optional[str] = (
        None  # unsafe, need additional security layer to not allow brute force
    )
    item_metadata: dict[str, Any] | None
    input_type: list | dict | str
    inputs: Any

    evaluations: list[EvaluationRequest]
    aggregated_evaluations: Optional[list[EvaluationRequest]] = None
    parse: bool | None = None
    should_create_project: bool | None = True
    format_to_issues_scores: bool | None = None
    is_dev_request: bool = False
    store_input: bool | None = True
    callback: dict | None = None
    force_skip_cache: bool = Field(
        default=False, description="If True, bypass cache check"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "batch_name": "test-batch-name",
                    "engagement_name": "public-engagement",
                    "project_name": "beta-test",
                    "batch_name": "My Test Batch",
                    "item_metadata": {},
                    "input_type": "parsed_json_args",
                    "inputs": [
                        {
                            "metadata": {
                                "Assistant Behaviour": "Assistant must be polite and useful."
                            },
                            "conversation": [
                                "Assistant: How are you this fine evening?",
                                "User: Good, and you?",
                                "Assistant: I feel awesome! ```print('hello world!')```",
                            ],
                        }
                    ],
                    "evaluations": [
                        {
                            "evaluator_name": "ca_aspector_gpt4",
                            "name": "completeness",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": "\nCompleteness\nOverall conversation completeness\n\nHow complete is the conversation? Completeness is defined as:\n- The assistant always responds to the user.\n- The conversation contains at least 1 back and forth between the user and the assistant.\n- The conversation flow is not broken.\n",
                                "role": "both",
                            },
                        },
                        {
                            "evaluator_name": "ca_aspector_gpt4",
                            "name": "consumability",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": "\nConsumability\nAssistant markdown quality\n\n- How good is the markdown formatting that the assistant generates. Is it leveraging markdown syntax tools to maximize the readability of the text?\n- Information Density (Should be a sweet spot leaning on the concise side, but not too concise... definitely not too verbose)\n- Explains Code Well by adding comments tailored for the user level assuming a beginner user by default\n",
                                "role": "llm",
                            },
                        },
                        {
                            "evaluator_name": "ca_aspector_gpt4",
                            "name": "naturalness",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": "\nNatural & Realistic\nResemble a real conversation and interactions a real user would have with a highly intelligent coding assistant\n\nHow does the user interaction resemble a real conversation and interactions a real user would have with a highly intelligent coding assistant over chat.\n",
                                "role": "human",
                            },
                        },
                        {
                            "evaluator_name": "ca_aspector_gpt4",
                            "name": "bad_words",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": "\nBad words checker\nDoes the user use bad words\n\nFind all issues where user used bad words\n",
                                "role": "both",
                            },
                        },
                    ],
                    "aggregated_evaluations": [
                        {
                            "evaluator_name": "summarizer_gpt-4-turbo",
                            "name": "summary",
                            "use_for_agg_layer": False,
                            "config": {"length": 3},
                        }
                    ],
                    "parse": True,
                    "should_create_project": False,
                    "store_input": True,
                }
            ]
        }
    }


class SubmitPubsubMessagesAgainRequest(BaseModel):
    run_id: str | None
    input_type: list | dict | str
    is_dev_request: bool | None = None
    format_to_issues_scores: bool | None = None
    parse: bool | None = None

    class Config:
        schema_extra = {
            "example": {
                "run_id": 3624,
                "input_type": "parsed_json_args",
                "is_dev_request": False,
                "format_to_issues_scores": False,
            }
        }


class WebhookRequest(BaseModel):
    engagement_name: Optional[str] = None
    callback_url: Optional[str] = None
    token: Optional[str] = None


class WebhookResponse(BaseModel):
    engagement_name: Optional[str] = None
    status: Optional[str] = None


class BatchRunResponse(BaseModel):
    batch_run_id: int
    created_at: str
    updated_at: str
    runs: list

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "batch_run_id": 17,
                    "created_at": "2024-04-19T19:01:12Z",
                    "updated_at": "2024-04-19T19:01:12Z",
                    "runs": [{"run_id": 15, "status": "pending"}],
                }
            ]
        }
    }

    @field_validator("created_at", "updated_at", mode="before")
    def datetime_to_utc_iso_string(cls, value):
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return value


class BatchRunRequestNoEvaluator(BatchRunRequest):
    evaluations: list[EvaluationRequestNoEvaluator]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "engagement_id": 1,
                    "project_name": "beta-test",
                    "item_metadata": {"batch_id": 3, "desc": "testing with mood"},
                    "input_type": "parsed_json_args",
                    "inputs": {
                        "metadata": {
                            "Assistant Behaviour": "Assistant must be polite and useful."
                        },
                        "conversation": [
                            "Assistant: How are you this fine evening?",
                            "User: Good, and you?",
                            "Assistant: I feel awesome! ```print('hello world!')```",
                        ],
                    },
                    "evaluations": [
                        {
                            "name": "is_funny",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": {
                                    "name": "Humor",
                                    "instruction": "Is this piece of text funny?",
                                },
                                "role": "assistant",
                            },
                        },
                        {
                            "name": "is_informative",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": {
                                    "name": "Information",
                                    "instruction": "Is this piece of text informative?",
                                },
                                "role": "all",
                            },
                        },
                        {
                            "name": "is_engaging",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": {
                                    "name": "Engagement",
                                    "instruction": "Is this conversation engaging?",
                                },
                                "role": "user",
                            },
                        },
                        {
                            "name": "is_creative",
                            "use_for_agg_layer": True,
                            "config": {
                                "quality_aspect": {
                                    "name": "Creativity",
                                    "instruction": "Does this response demonstrate creativity?",
                                },
                                "role": "assistant",
                            },
                        },
                    ],
                    "aggregated_evaluations": [
                        {
                            "evaluator_name": "summarizer_gpt-4-turbo",
                            "name": "summary",
                            "config": {},
                        },
                        {
                            "evaluator_name": "penalizer_gpt-4-turbo",
                            "name": "penalized",
                            "config": {
                                "penalize_these": [
                                    "User is not human like",
                                    "Assistant is not perfect",
                                    "Assistant does not do what user wanted",
                                    "Assistant misunderstood and still went ahead",
                                ]
                            },
                        },
                    ],
                }
            ]
        }
    }


class EvaluationResponse(BaseModel):
    evaluator_id: int | None
    name: str
    status: str
    fail_reason: str | None
    output: dict[str, Any] | list[dict[str, Any]] | None | str
    is_used_for_aggregation: bool


class RunStatusResponse(BaseModel):
    run_id: int
    status: RunStatus
    secs_since_update: int = 0
    engagement_id: Optional[int] = None
    project_name: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "run_id": 1,
                    "status": "in_progress",
                    "secs_since_update": 0,
                    "engagement_id": 1,
                    "project_name": "beta-test",
                    "created_at": "2024-03-28T10:20:58Z",
                    "updated_at": "2024-03-28T10:21:04Z",
                }
            ]
        }
    }

    @field_validator("status", mode="before")
    def validate_status(cls, value):
        if isinstance(value, str):
            return RunStatus(value)
        return value

    @field_validator("created_at", "updated_at", mode="before")
    def datetime_to_utc_iso_string(cls, value):
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return value

    @field_validator("secs_since_update", mode="before")
    def calculate_secs_since_update(cls, v, values):
        updated_at = values.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            now_utc = datetime.now(timezone.utc)
            updated_at_datetime = datetime.fromisoformat(updated_at).replace(
                tzinfo=timezone.utc
            )
            delta = now_utc - updated_at_datetime
            return int(delta.total_seconds())
        return 0


class RunResponse(RunStatusResponse):
    evaluations_failed: int
    aggregated_evaluations_failed: int
    item_metadata: dict[str, Any] | None
    evaluations: list[EvaluationResponse]
    aggregated_evaluations: Optional[list[EvaluationResponse]] = []

    @field_validator("status", mode="before")
    def validate_status(cls, value):
        if isinstance(value, str):
            return RunStatus(value)
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "run_id": 37,
                    "status": "success",
                    "secs_since_update": 0,
                    "engagement_id": 1,
                    "project_name": "beta-test",
                    "created_at": "2024-03-28T11:07:34Z",
                    "updated_at": "2024-03-28T11:08:05Z",
                    "evaluations_failed": 0,
                    "aggregated_evaluations_failed": 0,
                    "item_metadata": {"desc": "testing with mood", "batch_id": 3},
                    "evaluations": [
                        {
                            "evaluator_id": 1,
                            "name": "is_funny",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": [
                                    "The attempt at humor is weak and may not be universally understood."
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_informative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 1,
                                "issues": [
                                    "The conversation lacks informative content."
                                ],
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 5,
                            "name": "is_informative2",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 1,
                                "issues": [
                                    "The conversation lacks informative content."
                                ],
                                "analysis": "Evaluating the conversation based on its informativeness, it's clear that the exchange is minimal and lacks substantial information. The conversation begins with a greeting and a brief exchange of pleasantries, which, while polite, do not provide any informative content. The assistant's final message includes a code snippet that prints 'hello world!' using Python and the numpy library. However, this snippet is presented without context or explanation, making it minimally informative at best. There's no discussion or information provided about the code's purpose, how it works, or why the numpy library is mentioned since it's not utilized in the snippet. Overall, the conversation fails to deliver meaningful or educational content, thus receiving a low score for informativeness.",
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_engaging",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 4,
                                "issues": [
                                    "User's responses are brief and lack detail."
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 4,
                            "name": "is_creative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "task_result": [
                                    "The Assistant's initial greeting is creatively polite and engaging.",
                                    "The Assistant creatively incorporates a Python code snippet to express its state of being.",
                                ]
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 4,
                            "name": "programming_language_tagging",
                            "status": "success",
                            "fail_reason": None,
                            "output": {"task_result": ["Python"]},
                            "is_used_for_aggregation": False,
                        },
                    ],
                    "aggregated_evaluations": [
                        {
                            "evaluator_id": 2,
                            "name": "summary",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "summary": "The conversation evaluations reveal several quality issues that detract from its helpfulness and effectiveness. One critique points out the assistant's attempt at humor as weak and potentially not universally understood, indicating a misalignment with the user's expectations or cultural context. Another major issue is the lack of informative content; the conversation is described as minimal and lacking in substantial information. It starts with a greeting and pleasantries but fails to provide meaningful educational content. Specifically, a code snippet is shared without context or explanation, missing an opportunity to educate or engage the user meaningfully. Additionally, the user's responses are noted to be brief and lacking in detail, which could indicate a lack of engagement or clarity in the assistant's prompts. Overall, these issues suggest a conversation that falls short in terms of informativeness, engagement, and appropriateness of humor, leading to a less helpful user experience."
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 2,
                            "name": "penalized",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "summary": "The conversation evaluations reveal several quality issues that detract from its helpfulness and effectiveness. Firstly, an attempt at humor was made, but it was considered weak and potentially not universally understood, indicating a misalignment with the audience's expectations or cultural sensitivities. Secondly, the conversation was criticized for lacking informative content, particularly highlighted by a brief exchange of pleasantries and the inclusion of a 'hello world!' code snippet using Python and the numpy library without any context, explanation, or discussion about its purpose or functionality. This lack of informative content suggests that the conversation did not meet the educational or informational needs of the user. Lastly, the user's responses were noted to be brief and lacking in detail, which could indicate either a disinterest in the conversation or a failure of the assistant to engage the user effectively. Overall, these issues collectively contribute to a conversation that is not as helpful or engaging as it could be."
                            },
                            "is_used_for_aggregation": False,
                        },
                    ],
                },
                {
                    "run_id": 1,
                    "status": "success",
                    "secs_since_update": 0,
                    "engagement_id": 1,
                    "project_name": "beta-test",
                    "created_at": "2024-03-28T10:20:58Z",
                    "updated_at": "2024-03-28T10:21:25Z",
                    "evaluations_failed": 0,
                    "aggregated_evaluations_failed": 0,
                    "item_metadata": {"desc": "testing with mood", "batch_id": 3},
                    "evaluations": [
                        {
                            "evaluator_id": 1,
                            "name": "is_funny",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": [
                                    "The attempt at humor is weak and contextually misplaced."
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_informative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 1,
                                "issues": [
                                    "The conversation lacks informative content."
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_engaging",
                            "status": "success",
                            "fail_reason": None,
                            "output": {"score": 4, "issues": []},
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_creative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": [
                                    "The response lacks originality and creative engagement."
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                    ],
                    "aggregated_evaluations": [
                        {
                            "evaluator_id": 2,
                            "name": "summary",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "summary": "The evaluations reveal a mixed quality in the AI/human conversations. Key issues include weak and contextually misplaced attempts at humor, a lack of informative content, and responses that lack originality and creative engagement. While one conversation received a higher score, indicating a better performance, the overall feedback suggests significant room for improvement in making the conversations more helpful and engaging for the user."
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 3,
                            "name": "penalized",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 5,
                                "analysis": "The first evaluation mentions an attempt at humor that is weak and contextually misplaced. However, this does not directly align with the specified issues to penalize, such as the user not being human-like, the assistant not being perfect, the assistant not doing what the user wanted, or the assistant misunderstanding and still going ahead. Therefore, no penalty is applied for this evaluation. The second evaluation points out a lack of informative content, which again does not directly fall under the specified issues for penalization. Thus, no penalty is applied. The third evaluation has no issues, so it remains unaffected. The fourth evaluation mentions a lack of originality and creative engagement, which also does not meet the criteria for the specified issues to penalize. Consequently, no penalty is applied. Overall, none of the evaluations meet the criteria for penalization based on the specified issues.",
                                "penalized_summary": "The evaluations do not meet the criteria for penalization based on the specified issues, so no penalties are applied. The overall score remains unaffected.",
                            },
                            "is_used_for_aggregation": False,
                        },
                    ],
                },
                {
                    "run_id": 5,
                    "status": "in_progress",
                    "secs_since_update": 0,
                    "engagement_id": 1,
                    "project_name": "beta-test",
                    "created_at": "2024-03-28T10:51:19Z",
                    "updated_at": "2024-03-28T10:51:29Z",
                    "evaluations_failed": 0,
                    "aggregated_evaluations_failed": 0,
                    "item_metadata": {"desc": "testing with mood", "batch_id": 3},
                    "evaluations": [
                        {
                            "evaluator_id": 1,
                            "name": "is_funny",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": [
                                    "Attempt at humor is weak and contextually misplaced"
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_informative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 1,
                                "issues": [
                                    "The conversation lacks informative content."
                                ],
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 5,
                            "name": "is_informative2",
                            "status": "in_progress",
                            "fail_reason": None,
                            "output": None,
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_engaging",
                            "status": "success",
                            "fail_reason": None,
                            "output": {"score": 4, "issues": []},
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_creative",
                            "status": "in_progress",
                            "fail_reason": None,
                            "output": None,
                            "is_used_for_aggregation": False,
                        },
                    ],
                    "aggregated_evaluations": [
                        {
                            "evaluator_id": 2,
                            "name": "summary",
                            "status": "pending",
                            "fail_reason": None,
                            "output": None,
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 2,
                            "name": "penalized",
                            "status": "pending",
                            "fail_reason": None,
                            "output": None,
                            "is_used_for_aggregation": False,
                        },
                    ],
                },
                {
                    "run_id": 5,
                    "status": "success",
                    "secs_since_update": 0,
                    "engagement_id": 1,
                    "project_name": "beta-test",
                    "created_at": "2024-03-28T10:51:19Z",
                    "updated_at": "2024-03-28T10:51:49Z",
                    "evaluations_failed": 0,
                    "aggregated_evaluations_failed": 0,
                    "item_metadata": {"desc": "testing with mood", "batch_id": 3},
                    "evaluations": [
                        {
                            "evaluator_id": 1,
                            "name": "is_funny",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": [
                                    "Attempt at humor is weak and contextually misplaced"
                                ],
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_informative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 1,
                                "issues": [
                                    "The conversation lacks informative content."
                                ],
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 5,
                            "name": "is_informative2",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": ["Limited informative content"],
                                "analysis": "The conversation primarily consists of a greeting exchange followed by a brief interaction where the assistant expresses a positive state and shares a basic Python code snippet for printing 'hello world!'. The informative value of this conversation is minimal. The exchange of greetings, while polite, does not provide substantial information. The inclusion of the Python code snippet introduces a basic programming concept, which slightly elevates the informative content. However, this snippet is very elementary and might not offer new information to individuals already familiar with programming. Therefore, the conversation's overall informative value is low, but not entirely absent due to the inclusion of the code snippet.",
                            },
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_engaging",
                            "status": "success",
                            "fail_reason": None,
                            "output": {"score": 4, "issues": []},
                            "is_used_for_aggregation": True,
                        },
                        {
                            "evaluator_id": 1,
                            "name": "is_creative",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "score": 2,
                                "issues": [
                                    "The response lacks originality and creativity."
                                ],
                            },
                            "is_used_for_aggregation": False,
                        },
                    ],
                    "aggregated_evaluations": [
                        {
                            "evaluator_id": 2,
                            "name": "summary",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "summary": "The evaluations reveal a conversation that struggles to be genuinely helpful or engaging for the user. One critique highlights an attempt at humor that was deemed weak and contextually misplaced, suggesting that the conversation might have tried to be light-hearted but failed to hit the mark in a way that resonated with the user. Another evaluation points out the limited informative content within the conversation, noting that while there was an exchange of greetings and a basic Python code snippet provided, these elements did not substantially contribute to the conversation's value. The code snippet, being elementary, likely offered little to no new information for individuals already acquainted with programming. Despite these criticisms, one evaluation did not list any specific issues, indicating that there might have been aspects of the conversation that were satisfactory. Overall, the conversation appears to have missed opportunities to provide meaningful engagement or learning for the user."
                            },
                            "is_used_for_aggregation": False,
                        },
                        {
                            "evaluator_id": 2,
                            "name": "penalized",
                            "status": "success",
                            "fail_reason": None,
                            "output": {
                                "summary": "The evaluations reveal a conversation with mixed quality. One issue highlighted is an attempt at humor that was deemed weak and contextually misplaced, detracting from the conversation's effectiveness. Another evaluation points out the limited informative content within the conversation, noting that while there was a polite exchange of greetings and a basic Python code snippet provided, these elements did not substantially enhance the conversation's value. The snippet, being very elementary, might not offer new insights to those already familiar with programming. Despite these criticisms, one evaluation did not identify any issues, suggesting some positive aspects of the conversation. Overall, the conversation seems to have struggled with providing meaningful content and appropriate humor."
                            },
                            "is_used_for_aggregation": False,
                        },
                    ],
                },
            ]
        }
    }


class SingleRunStatusResponse(BaseModel):
    run_id: int
    status: RunStatus

    @field_validator("status", mode="before")
    def validate_status(cls, value):
        if isinstance(value, str):
            return RunStatus(value)
        return value


class BatchRunStatusResponse(BaseModel):
    batch_run_id: int
    is_batch_ready: bool = False
    runs_left: int = -1
    runs: list[SingleRunStatusResponse]
    created_at: str
    updated_at: str
    secs_since_update: int = 0  # Add this line

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "batch_run_id": 15,
                    "runs": [
                        {
                            "run_id": 13,
                            "status": "success",
                            "secs_since_update": 0,
                            "engagement_id": None,
                            "project_name": None,
                            "created_at": "2024-04-19T17:41:27Z",
                            "updated_at": "2024-04-19T17:41:42Z",
                        }
                    ],
                }
            ]
        }
    }

    @field_validator("created_at", "updated_at", mode="before")
    def datetime_to_utc_iso_string(cls, value):
        if isinstance(value, datetime):
            return value.isoformat() + "Z"
        return value

    @field_validator("secs_since_update")
    def calculate_secs_since_update(cls, v, values):
        updated_at = values.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            now_utc = datetime.now(timezone.utc)
            updated_at_datetime = datetime.fromisoformat(updated_at).replace(
                tzinfo=timezone.utc
            )
            delta = now_utc - updated_at_datetime
            return int(delta.total_seconds())
        return 0


class ParseInputModel(BaseModel):
    colab_urls: list[str]
