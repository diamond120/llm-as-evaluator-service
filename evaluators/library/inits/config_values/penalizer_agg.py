from evaluators.library.inits.schemas.type.generic import (
    GenericEvaluatorTypeConfigSchema,
)

evaluator_name = "penalizer"
evaluator_description = "Penalize something in the first stage."
evaluator_config = GenericEvaluatorTypeConfigSchema(
    system_prompt="""
Given the following reviews of AI/human conversations and its quality issues, please penalize selected types of issues.
This is a conversation created for the purposes of training an AI fully by human. Human role plays both sides. The data must be as close to ideal as possible.

# Issues to penalize:
{penalize_these}
""",
    first_user_message="""Evaluations:
```
{evaluations}
```
DO NOT COPY EVALUATIONS IN JSON YOU WERE PROVIDED THIS TO THE OUTPUT.
""",
)
