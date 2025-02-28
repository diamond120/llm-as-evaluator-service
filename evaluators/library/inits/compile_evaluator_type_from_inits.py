from evaluators.library.inits.schemas.type.aspector import (
    EvaluatorTypeConfigSchemaAspector,
)
from evaluators.library.inits.schemas.type.cellwise_aspector import (
    EvaluatorTypeConfigSchemaCellwiseAspector,
)
from evaluators.library.inits.schemas.type.generic import (
    GenericEvaluatorTypeConfigSchema,
)

# Create a new EvaluatorType object for the quality aspector
quality_aspector_evaluator_type = dict(
    name="single_stage_system_prompt_aspector",
    description="Basic insert quality aspect and review version.",
    config_schema=EvaluatorTypeConfigSchemaAspector.model_json_schema(),
)
cellwise_quality_aspector_evaluator_type = dict(
    name="single_stage_system_prompt_cellwise_aspector",
    description="Basic insert quality aspect and review version but per row.",
    config_schema=EvaluatorTypeConfigSchemaCellwiseAspector.model_json_schema(),
)

generic_evaluator_type = dict(
    name="single_stage_system_prompt",
    description="Generic evaluator type",
    config_schema=GenericEvaluatorTypeConfigSchema.model_json_schema(),
)
