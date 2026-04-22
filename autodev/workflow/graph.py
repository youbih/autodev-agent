from langgraph.graph import StateGraph, END

from autodev.workflow.state import ProjectState
from autodev.agents.architect import architect_node
from autodev.agents.human import human_review_node, route_after_review
from autodev.agents.coder import coder_node
from autodev.agents.qa import qa_node
from autodev.agents.tech_writer import tech_writer_node


def route_after_qa(state: ProjectState) -> str:
    if not state.get("test_passed", False):
        return "coder"
    return "tech_writer"


def build_graph():
    workflow = StateGraph(ProjectState)

    workflow.add_node("architect", architect_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("tech_writer", tech_writer_node)

    workflow.set_entry_point("architect")
    workflow.add_edge("architect", "human_review")

    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "architect": "architect",
            "coder": "coder",
        },
    )

    workflow.add_edge("coder", "qa")

    workflow.add_conditional_edges(
        "qa",
        route_after_qa,
        {
            "coder": "coder",
            "tech_writer": "tech_writer",
        },
    )

    workflow.add_edge("tech_writer", END)

    return workflow.compile()