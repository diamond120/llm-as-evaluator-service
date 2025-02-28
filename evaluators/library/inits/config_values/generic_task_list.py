from evaluators.library.inits.schemas.type.generic import (
    GenericEvaluatorTypeConfigSchema,
)

evaluator_name = "generic_task_executor_list"
evaluator_description = "Basic insert task and execute version."
evaluator_config = GenericEvaluatorTypeConfigSchema(
    system_prompt="""
Given the following conversation between AI/human, please, do the following task and output your answer for the task as result:
{task}

Task has a set of instructions, usually in the form of a question about the conversation. Provide your replies in the task output list as strings!

Please, focus only on the task in question. Any other issues not related to this task aspect MUST BE IGNORED BY YOU!
""",
    first_user_message="""Conversation metadata:
```
{metadata}
```

Conversation between AI Assistant and a human User:
```
{conversation}
```""",
)
