"""Thin service layer between the API routes and the compiled graph.

Routes stay dumb: they parse the request, call a function here, and shape
the response. All graph invocation and state-shaping logic lives here so it
stays testable without an HTTP client.
"""

from __future__ import annotations

from typing import Any

from app.graph.state import BookingDraft


def _message_role(msg: Any) -> str:
    return "user" if getattr(msg, "type", None) == "human" else "assistant"


def _serialize_booking(booking: BookingDraft | None) -> dict:
    return (booking or BookingDraft()).model_dump()


async def run_chat(graph: Any, thread_id: str, message: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}

    prior = await graph.aget_state(config)
    before_count = len(prior.values.get("messages", [])) if prior.values else 0

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )

    # +1 skips the human message we just sent; everything after it is new
    # assistant output produced during this turn (one message normally, two
    # when an FAQ detour resumes a booking in the same turn).
    new_messages = result["messages"][before_count + 1 :]
    new_assistant = [m for m in new_messages if getattr(m, "type", None) == "ai"]

    return {
        "thread_id": thread_id,
        "reply": "\n\n".join(m.content for m in new_assistant),
        "new_messages": [{"role": "assistant", "content": m.content} for m in new_assistant],
        "active_node": result.get("active_node", ""),
        "citations": result.get("citations", []),
        "booking": _serialize_booking(result.get("booking")),
    }


async def get_thread_state(graph: Any, thread_id: str) -> dict | None:
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    if not state.values:
        return None

    messages = [
        {"role": _message_role(m), "content": m.content}
        for m in state.values.get("messages", [])
    ]

    return {
        "thread_id": thread_id,
        "messages": messages,
        "booking": _serialize_booking(state.values.get("booking")),
        "citations": state.values.get("citations", []),
    }
