from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SmokeState(TypedDict):
    message: str
    normalized: str
    status: str


def normalize(state: SmokeState) -> dict[str, str]:
    return {"normalized": state["message"].strip().lower()}


def complete(_: SmokeState) -> dict[str, str]:
    return {"status": "completed"}


_builder = StateGraph(SmokeState)
_builder.add_node("normalize", normalize)
_builder.add_node("complete", complete)
_builder.add_edge(START, "normalize")
_builder.add_edge("normalize", "complete")
_builder.add_edge("complete", END)
smoke_graph = _builder.compile()


def run_smoke_workflow(message: str) -> SmokeState:
    return smoke_graph.invoke(
        {"message": message, "normalized": "", "status": "pending"}
    )
