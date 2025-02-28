from evaluators.library.inits.schemas.type.generic import (
    GenericEvaluatorTypeConfigSchema,
)

evaluator_name = "tagging"
evaluator_description = "Tag this data!"
evaluator_config = GenericEvaluatorTypeConfigSchema(
    system_prompt="""
Given the following conversation between AI and human, please, perform tagging operation.
Tagging operation is when you evaluate a piece of data and list certain attributes about this data that were requested. In this case, the data is the whole conversation.

Follow these rules for tagging the conversation:
{tagging_rules}

Provide your tags in the tagging output list as strings!

Please, focus only on the task in question. Any other issues not related to this task aspect MUST BE IGNORED BY YOU!
""",
    first_user_message="""
Conversation between AI Assistant and a human User:
```
{conversation}
```""",
)
