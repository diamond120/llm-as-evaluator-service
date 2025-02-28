from langgraph.graph import END, START, StateGraph
from evaluators.graph_llm_modules.state import State


def get_runnable_graph():

    workflow = StateGraph(State)

    from evaluators.graph_llm_modules.state_functions import (
        comparative_reviewer, 
        direct_reviewer,
        issue_eliminator,
        meta_reviewer,
        user_prompt_reviewer
    )

    workflow.add_node("user_prompt_reviewer", user_prompt_reviewer)
    workflow.add_node("direct_reviewer", direct_reviewer)
    workflow.add_node("comparative_reviewer", comparative_reviewer)
    workflow.add_node("meta_reviewer", meta_reviewer)
    workflow.add_node("issue_eliminator", issue_eliminator)

    workflow.add_edge(START, "user_prompt_reviewer")
    workflow.add_edge("user_prompt_reviewer", "direct_reviewer")
    workflow.add_edge("direct_reviewer", "comparative_reviewer")
    workflow.add_edge("comparative_reviewer", "meta_reviewer")
    workflow.add_edge("meta_reviewer", "issue_eliminator")
    workflow.add_edge("issue_eliminator", END)

    app = workflow.compile()

    return app
