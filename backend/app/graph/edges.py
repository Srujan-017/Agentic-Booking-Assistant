from __future__ import annotations

from langgraph.graph import END

from app.graph.state import AgentState, BookingDraft


def route_after_guardrail(state: AgentState) -> str:
    return END if state.get("intent") == "blocked" else "router"


def route_after_router(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "faq":
        return "rag"
    if intent == "booking":
        return "booking"
    if intent == "mixed":
        return "booking_extract"
    return "general"


def _booking_in_progress(state: AgentState) -> bool:
    booking: BookingDraft = state.get("booking") or BookingDraft()
    return booking.status == "collecting"


def route_after_rag(state: AgentState) -> str:
    return "booking" if _booking_in_progress(state) else END


def route_after_general(state: AgentState) -> str:
    return "booking" if _booking_in_progress(state) else END
