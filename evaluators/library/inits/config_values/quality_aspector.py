from evaluators.library.inits.schemas.type.aspector import (
    EvaluatorTypeConfigSchemaAspector,
)

evaluator_name = "quality_aspector"
evaluator_description = "Basic insert quality aspect and review version."
evaluator_config = EvaluatorTypeConfigSchemaAspector(
    system_prompt="""
Given the following conversation, please rate the quality of the conversation according to the given quality aspect. You are one of many specialized inspectors, so precisely focus on your quality aspect. Do not overstep your scope.

Quality Aspect:
{quality_aspect}
IMPORTANT: Please, focus only on the quality aspect in question. Any other issues not related to this quality aspect MUST BE IGNORED BY YOU!
""",
    first_user_message="""# Conversation metadata:
METADATA_START
```
{metadata}
```
METADATA_END

# Conversation between AI Assistant and a human User:
CONVERSATION_START
```
{conversation}
```
CONVERSATION_END

IMPORTANT: Please, focus only on the quality aspect in question. Any other issues not related to this quality aspect MUST BE IGNORED BY YOU!
""",
    role_map={
        "user": "ONLY JUDGE THE USER MESSAGES. DO NOT JUDGE THE ASSISTANT MESSAGES.",
        "assistant": "ONLY JUDGE THE ASSISTANT MESSAGES. DO NOT JUDGE THE USER MESSAGES.",
        "all": "JUDGE THE ENTIRE CONVERSATION AS A WHOLE.",
    },
)
