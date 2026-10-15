from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.graph.edges import (
    route_after_general,
    route_after_guardrail,
    route_after_rag,
    route_after_router,
)
from app.graph.nodes.booking import booking_node
from app.graph.nodes.booking_extract import booking_extract_node
from app.graph.nodes.general import general_node
from app.graph.nodes.guardrail import guardrail_node
from app.graph.nodes.rag import rag_node
from app.graph.nodes.router import router_node
from app.graph.state import AgentState


def build_graph(checkpointer: BaseCheckpointSaver):
    graph = StateGraph(AgentState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("router", router_node)
    graph.add_node("rag", rag_node)
    graph.add_node("booking_extract", booking_extract_node)
    graph.add_node("booking", booking_node)
    graph.add_node("general", general_node)

    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges(
        "guardrail", route_after_guardrail, {"router": "router", END: END}
    )
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "rag": "rag",
            "booking": "booking",
            "booking_extract": "booking_extract",
            "general": "general",
        },
    )
    graph.add_edge("booking_extract", "rag")
    graph.add_conditional_edges("rag", route_after_rag, {"booking": "booking", END: END})
    graph.add_conditional_edges(
        "general", route_after_general, {"booking": "booking", END: END}
    )
    graph.add_edge("booking", END)

    return graph.compile(checkpointer=checkpointer)
