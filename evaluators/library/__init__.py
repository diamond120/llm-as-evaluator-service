from evaluators.library.apple_code_translation_evaluator import (
    AppleCodeTranslationEvaluator,
)
from evaluators.library.apple_llm_reviewer_proxy import AppleLLMReviewerProxy
from evaluators.library.apple_tbt_evaluator import AppleTurnByTurnEvaluator
from evaluators.library.cbc_two_stage import CBCTwoStageEvaluator
from evaluators.library.echo import EchoSingleStageMessagesEvaluator
from evaluators.library.graph_code_checker import GraphCodeCheckerEvaluator
from evaluators.library.graph_llm_evaluator import GraphLLMEvaluator
from evaluators.library.rlhf_conversation import RLHFEvaluator
from evaluators.library.rlhf_global_evaluator import RLHFGlobalEvaluator
from evaluators.library.single_stage_messages import SingleStageMessagesEvaluator
from evaluators.library.single_stage_system_prompt import (
    SingleStageSystemPromptEvaluator,
)
from evaluators.library.single_stage_system_prompt_aspector import (
    SingleStageSystemPromptAspectorEvaluator,
)
from evaluators.library.single_stage_system_prompt_cellwise_aspector import (
    SingleStageSystemPromptCellwiseAspectorEvaluator,
)
from evaluators.library.specific_single_stage_system_prompt_aspector import (
    SpecificSingleStageSystemPromptAspectorEvaluator,
)
from evaluators.library.unified_text_field_grammar_evaluator import (
    UnifiedTextFieldGrammarEvaluator,
)

# apple new
from evaluators.library.notebook_code_compatibility_evaluator import (
    ExecutionCompatabilityEvaluator,
)
from evaluators.library.plagiarism_checker import (
    EvaluationPlagiarismChecker,
)
from evaluators.library.ai_gen_checker import EvaluationAIChecker
from evaluators.library.linting_evaluator import LintingEvaluator
from evaluators.library.code_formatting_evaluator import CodeFormatEvaluator
