"""Lightweight extraction-only node used for "mixed" messages (booking details
+ a separate handbook question in one message), so the booking fields are
saved into state BEFORE the rag node runs. No reply is generated here; the
full booking_node (which re-runs extraction defensively) produces the reply
after rag, so the turn reads as one continuous answer."""

from __future__ import annotations

from app.graph.nodes.booking import extract_and_merge_fields
from app.graph.state import AgentState, BookingDraft


async def booking_extract_node(state: AgentState) -> dict:
    booking: BookingDraft = state.get("booking") or BookingDraft()
    if booking.status in ("idle", "confirmed"):
        booking = BookingDraft(status="collecting")

    updated, _invalid_email_given = await extract_and_merge_fields(state, booking)
    return {"booking": updated, "active_node": "booking_extract"}
