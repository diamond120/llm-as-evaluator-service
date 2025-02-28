from evaluators.library.inits.schemas.type.generic import (
    GenericEvaluatorTypeConfigSchema,
)

evaluator_name = "summarizer"
evaluator_description = "Summarize second second stage."
evaluator_config = GenericEvaluatorTypeConfigSchema(
    system_prompt="""
Given the following reviews of AI/human conversations and its quality issues, please summarize overall feel from the conversation.
Really focus on the issues that make this conversation not helpful for the user or where Assistant is doing something that User did not ask. Or where Assistant did not do a good job of being perfect.
""",
    first_user_message="""Evaluations:
```
{evaluations}
```
DO NOT COPY EVALUATIONS IN JSON YOU WERE PROVIDED THIS TO THE OUTPUT.
""",
)
