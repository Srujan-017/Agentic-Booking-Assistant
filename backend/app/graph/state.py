from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, EmailStr


class BookingDraft(BaseModel):
    service_type: str | None = None
    name: str | None = None
    email: str | None = None
    slot_id: int | None = None
    slot_label: str | None = None
    status: Literal["idle", "collecting", "confirmed"] = "idle"
    reference_id: str | None = None

    def is_complete_for_slot_selection(self) -> bool:
        return bool(self.name and self.email)


class Citation(TypedDict):
    page: int
    source: str
    snippet: str


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Literal["faq", "booking", "mixed", "general", "blocked"] | None
    faq_question: str | None
    booking: BookingDraft
    citations: list[Citation]
    active_node: str


def fresh_state(user_message: str) -> dict:
    """Input dict for graph.ainvoke on a new turn. Only new content goes in;
    LangGraph merges it onto the persisted state for the thread via the
    checkpointer, and `add_messages` appends rather than replaces."""
    return {
        "messages": [{"role": "user", "content": user_message}],
    }


class EmailCheck(BaseModel):
    email: EmailStr
