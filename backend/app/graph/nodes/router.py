from __future__ import annotations

from typing import Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from app.graph.llm import get_router_llm
from app.graph.prompts import ROUTER_SYSTEM
from app.graph.state import AgentState, BookingDraft

MAX_HISTORY_MESSAGES = 12


class RouteDecision(BaseModel):
    intent: Literal["faq", "booking", "mixed", "general"]
    faq_question: str | None = None
    reasoning: str = ""


async def router_node(state: AgentState) -> dict:
    booking: BookingDraft = state.get("booking") or BookingDraft()

    system = ROUTER_SYSTEM.format(
        booking_status=booking.status,
        name=booking.name or "(none)",
        email=booking.email or "(none)",
        slot_label=booking.slot_label or "(none)",
    )

    history = state["messages"][-MAX_HISTORY_MESSAGES:]
    llm = get_router_llm().with_structured_output(RouteDecision)
    decision: RouteDecision = await llm.ainvoke([SystemMessage(content=system), *history])

    # Citations reflect only the current turn's RAG lookup, if any. Clear
    # them here so a non-faq turn (booking/general) doesn't re-display a
    # stale citation from an earlier, unrelated question.
    update: dict = {"intent": decision.intent, "active_node": "router", "citations": []}
    if decision.intent == "mixed":
        update["faq_question"] = decision.faq_question
    else:
        update["faq_question"] = None
    return update
