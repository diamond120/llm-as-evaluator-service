from evaluators.library.inits.schemas.type.cellwise_aspector import (
    EvaluatorTypeConfigSchemaCellwiseAspector,
)

evaluator_name = "cellwise_quality_aspector"
evaluator_description = (
    "Basic insert quality aspect and review version but on per cell basis."
)
evaluator_config = EvaluatorTypeConfigSchemaCellwiseAspector(
    system_prompt="""
Given the following part of a greater conversation, please rate the quality of this cell according to the given quality aspect. You are one of many specialized inspectors, so precisely focus on your quality aspect. Do not overstep your scope.

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

# Cell part of a conversation between AI Assistant and a human User:
CONVERSATION_CELL_START
```
{conversation_cell}
```
CONVERSATION_CELL_END

IMPORTANT: Please, focus only on the quality aspect in question. Any other issues not related to this quality aspect MUST BE IGNORED BY YOU!
""",
)
