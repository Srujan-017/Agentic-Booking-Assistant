from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage

from app.graph.llm import get_main_llm
from app.graph.prompts import GENERAL_SYSTEM
from app.graph.state import AgentState


async def general_node(state: AgentState) -> dict:
    llm = get_main_llm()
    history = state["messages"][-6:]
    response = await llm.ainvoke([SystemMessage(content=GENERAL_SYSTEM), *history])
    return {
        "messages": [AIMessage(content=response.content)],
        "active_node": "general",
    }
