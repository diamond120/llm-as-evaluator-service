from evaluators.library.inits.compile_evaluator_type_from_inits import (
    cellwise_quality_aspector_evaluator_type,
    generic_evaluator_type,
    quality_aspector_evaluator_type,
)
from evaluators.library.inits.config_values.cellwise_quality_aspector import (
    evaluator_config as cellwise_aspector_evaluator_config,
)
from evaluators.library.inits.config_values.cellwise_quality_aspector import (
    evaluator_description as cellwise_aspector_evaluator_description,
)
from evaluators.library.inits.config_values.cellwise_quality_aspector import (
    evaluator_name as cellwise_aspector_evaluator_name,
)
from evaluators.library.inits.config_values.code_reviewer import (
    evaluator_config as code_reviewer_evaluator_config,
)
from evaluators.library.inits.config_values.code_reviewer import (
    evaluator_description as code_reviewer_evaluator_description,
)
from evaluators.library.inits.config_values.code_reviewer import (
    evaluator_name as code_reviewer_evaluator_name,
)
from evaluators.library.inits.config_values.generic_task_list import (
    evaluator_config as generic_task_list_evaluator_config,
)
from evaluators.library.inits.config_values.generic_task_list import (
    evaluator_description as generic_task_list_evaluator_description,
)
from evaluators.library.inits.config_values.generic_task_list import (
    evaluator_name as generic_task_list_evaluator_name,
)
from evaluators.library.inits.config_values.penalizer_agg import (
    evaluator_config as penalizer_evaluator_config,
)
from evaluators.library.inits.config_values.penalizer_agg import (
    evaluator_description as penalizer_evaluator_description,
)
from evaluators.library.inits.config_values.penalizer_agg import (
    evaluator_name as penalizer_evaluator_name,
)
from evaluators.library.inits.config_values.quality_aspector import (
    evaluator_config as aspector_evaluator_config,
)
from evaluators.library.inits.config_values.quality_aspector import (
    evaluator_description as aspector_evaluator_description,
)
from evaluators.library.inits.config_values.quality_aspector import (
    evaluator_name as aspector_evaluator_name,
)
from evaluators.library.inits.config_values.summarizer_agg import (
    evaluator_config as summarizer_evaluator_config,
)
from evaluators.library.inits.config_values.summarizer_agg import (
    evaluator_description as summarizer_evaluator_description,
)
from evaluators.library.inits.config_values.summarizer_agg import (
    evaluator_name as summarizer_evaluator_name,
)
from evaluators.library.inits.config_values.tagging import (
    evaluator_config as tagging_evaluator_config,
)
from evaluators.library.inits.config_values.tagging import (
    evaluator_description as tagging_evaluator_description,
)
from evaluators.library.inits.config_values.tagging import (
    evaluator_name as tagging_evaluator_name,
)
from evaluators.library.inits.schemas.instance.aspector import (
    AspectFeedback,
    AspectorEvaluatorInputSchema,
)
from evaluators.library.inits.schemas.instance.aspector_with_thinking_field import (
    AspectFeedbackWithThinking,
)
from evaluators.library.inits.schemas.instance.cellwise_aspector import (
    CellwiseAspectFeedbackItem,
    CellwiseAspectorEvaluatorInputSchema,
)
from evaluators.library.inits.schemas.instance.code_reviewer import (
    CodeReview,
    CodeReviewerEvaluatorInputSchema,
)
from evaluators.library.inits.schemas.instance.generic_task_list import (
    GenericTaskEvaluatorInputSchema,
    TaskResult,
)
from evaluators.library.inits.schemas.instance.penalizer import (
    PenalizeEvaluatorInputSchema,
    PenalizerOutput,
)
from evaluators.library.inits.schemas.instance.summarizer import (
    SummarizeEvaluatorInputSchema,
    SummaryEvaluation,
)
from evaluators.library.inits.schemas.instance.tagging import (
    TaggingEvaluatorInputSchema,
    TaggingResult,
)

llm_config = {
    "llm_provider": "openai_api",  # or "groq_api"
    "llm_model": "gpt-4-turbo",  # or "mixtral-8x7b-32768"
    "llm_params": {"temperature": 0, "max_tokens": 4000},
}
print(CellwiseAspectFeedbackItem.model_json_schema())

cellwise_quality_aspector_evaluator = dict(
    name=cellwise_aspector_evaluator_name + "4",
    project_id=None,
    evaluator_type_name=cellwise_quality_aspector_evaluator_type["name"],
    description=cellwise_aspector_evaluator_description,
    config=cellwise_aspector_evaluator_config.dict(),
    **llm_config,
    input_schema=CellwiseAspectorEvaluatorInputSchema.model_json_schema(),
    output_schema=CellwiseAspectFeedbackItem.model_json_schema(),  # single output, also add flag to aspector that it output multiple items of this schema
)

quality_aspector_evaluator = dict(
    name=aspector_evaluator_name,
    project_id=None,
    evaluator_type_name=quality_aspector_evaluator_type["name"],
    description=aspector_evaluator_description,
    config=aspector_evaluator_config.dict(),
    **llm_config,
    input_schema=AspectorEvaluatorInputSchema.model_json_schema(),
    output_schema=AspectFeedback.model_json_schema(),
)

quality_aspector_evaluator_with_thinking_field = dict(
    name=aspector_evaluator_name + "_with_thinking_field",
    project_id=None,
    evaluator_type_name=quality_aspector_evaluator_type["name"],
    description=aspector_evaluator_description,
    config=aspector_evaluator_config.dict(),
    **llm_config,
    input_schema=AspectorEvaluatorInputSchema.model_json_schema(),
    output_schema=AspectFeedbackWithThinking.model_json_schema(),
)

# Summarizer Evaluator Configuration
summarizer_evaluator = dict(
    name=summarizer_evaluator_name,
    project_id=None,
    evaluator_type_name=generic_evaluator_type["name"],
    description=summarizer_evaluator_description,
    config=summarizer_evaluator_config.dict(),
    **llm_config,
    input_schema=SummarizeEvaluatorInputSchema.model_json_schema(),
    output_schema=SummaryEvaluation.model_json_schema(),
)

# Penalizer Evaluator Configuration
penalizer_evaluator = dict(
    name=penalizer_evaluator_name,
    project_id=None,
    evaluator_type_name=generic_evaluator_type["name"],
    description=penalizer_evaluator_description,
    config=penalizer_evaluator_config.dict(),
    **llm_config,
    input_schema=PenalizeEvaluatorInputSchema.model_json_schema(),
    output_schema=PenalizerOutput.model_json_schema(),
)

# Generic Task Evaluator Configuration
generic_task_evaluator = dict(
    name=generic_task_list_evaluator_name,
    project_id=None,
    evaluator_type_name=generic_evaluator_type["name"],
    description=generic_task_list_evaluator_description,
    config=generic_task_list_evaluator_config.dict(),
    **llm_config,
    input_schema=GenericTaskEvaluatorInputSchema.model_json_schema(),
    output_schema=TaskResult.model_json_schema(),
)

# Code review Evaluator Configuration
code_review_evaluator = dict(
    name=code_reviewer_evaluator_name,
    project_id=None,
    evaluator_type_name=generic_evaluator_type["name"],
    description=code_reviewer_evaluator_description,
    config=code_reviewer_evaluator_config.dict(),
    **llm_config,
    input_schema=CodeReviewerEvaluatorInputSchema.model_json_schema(),
    output_schema=CodeReview.model_json_schema(),
)


tagging_evaluator = dict(
    name=tagging_evaluator_name,
    project_id=None,
    evaluator_type_name=generic_evaluator_type["name"],
    description=tagging_evaluator_description,
    config=tagging_evaluator_config.dict(),
    **llm_config,
    input_schema=TaggingEvaluatorInputSchema.model_json_schema(),
    output_schema=TaggingResult.model_json_schema(),
)

llm_config = {
    "llm_provider": "groq_api",  # or "groq_api"
    "llm_model": "mixtral-8x7b-32768",  # or "mixtral-8x7b-32768"
    "llm_params": {"temperature": 0, "max_tokens": 4000},
}

tagging_evaluator_groq_mixtral = dict(
    name=tagging_evaluator_name + "groq",
    project_id=None,
    evaluator_type_name=generic_evaluator_type["name"],
    description=tagging_evaluator_description,
    config=tagging_evaluator_config.dict(),
    **llm_config,
    input_schema=TaggingEvaluatorInputSchema.model_json_schema(),
    output_schema=TaggingResult.model_json_schema(),
)
