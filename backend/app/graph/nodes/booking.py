from __future__ import annotations

from pydantic import BaseModel, ValidationError

from langchain_core.messages import AIMessage, SystemMessage

from app.graph.llm import get_main_llm, get_router_llm
from app.graph.prompts import BOOKING_EXTRACT_SYSTEM, BOOKING_SYSTEM
from app.graph.state import AgentState, BookingDraft, EmailCheck
from app.services import slot_store
from app.tools.booking_tools import book_slot

DEFAULT_SERVICE_TYPE = "Performance Review"


class ExtractedBookingFields(BaseModel):
    name: str | None = None
    email: str | None = None
    service_type: str | None = None
    slot_id: int | None = None


def _format_slots_listing(slots: list[dict]) -> str:
    if not slots:
        return "(no slots currently available)"
    return "\n".join(
        f"{i + 1}. {s['label']} (slot_id={s['id']})" for i, s in enumerate(slots)
    )


def _last_user_text(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if getattr(msg, "type", None) == "human":
            return msg.content
    return ""


async def extract_and_merge_fields(
    state: AgentState, booking: BookingDraft
) -> tuple[BookingDraft, bool]:
    """Extract any new fields from the latest message and merge them onto the
    draft. Only overwrites a field when the extraction found a new value, so
    fields collected on earlier turns survive (this is how interleaving keeps
    name/email across an FAQ detour). Returns (updated_draft, invalid_email_given)."""
    message = _last_user_text(state)
    if not message.strip():
        return booking, False

    available = await slot_store.list_available_slots()
    slots_listing = _format_slots_listing(available)

    system = BOOKING_EXTRACT_SYSTEM.format(slots_listing=slots_listing)
    llm = get_router_llm().with_structured_output(ExtractedBookingFields)
    extracted: ExtractedBookingFields = await llm.ainvoke(
        [SystemMessage(content=system), {"role": "user", "content": message}]
    )

    updated = booking.model_copy()
    if extracted.name:
        updated.name = extracted.name
    if extracted.service_type:
        updated.service_type = extracted.service_type

    invalid_email_given = False
    if extracted.email:
        try:
            EmailCheck(email=extracted.email)
            updated.email = extracted.email
        except ValidationError:
            invalid_email_given = True

    if extracted.slot_id is not None:
        valid_ids = {s["id"] for s in available}
        if extracted.slot_id in valid_ids:
            updated.slot_id = extracted.slot_id
            updated.slot_label = next(
                s["label"] for s in available if s["id"] == extracted.slot_id
            )

    return updated, invalid_email_given


async def _reply(situation: str, booking: BookingDraft, resuming: bool, slots_listing: str) -> str:
    first_name = (booking.name or "").split(" ")[0] if booking.name else ""
    system = BOOKING_SYSTEM.format(
        name=booking.name or "(missing)",
        email=booking.email or "(missing)",
        slot_label=booking.slot_label or "(not chosen yet)",
        service_type=booking.service_type or DEFAULT_SERVICE_TYPE,
        first_name=first_name or "there",
        slots_listing=slots_listing,
    )
    llm = get_main_llm()
    response = await llm.ainvoke(
        [
            SystemMessage(content=system),
            {
                "role": "user",
                "content": (
                    f"Situation: {situation}\n"
                    f"resuming_after_faq: {resuming}\n"
                    "Write the next reply to the user now."
                ),
            },
        ]
    )
    return response.content


async def booking_node(state: AgentState) -> dict:
    resuming_after_faq = state.get("active_node") == "rag"

    booking: BookingDraft = state.get("booking") or BookingDraft()
    if booking.status in ("idle", "confirmed"):
        booking = BookingDraft(status="collecting")

    booking, invalid_email_given = await extract_and_merge_fields(state, booking)

    available = await slot_store.list_available_slots()
    slots_listing = _format_slots_listing(available)

    if invalid_email_given:
        reply = await _reply(
            "The email just provided is not a valid email address. Ask the user "
            "to re-enter a valid email. Do not proceed to slots yet.",
            booking,
            resuming_after_faq,
            slots_listing,
        )
        return {"booking": booking, "active_node": "booking", "messages": [AIMessage(content=reply)]}

    if not booking.is_complete_for_slot_selection():
        missing = []
        if not booking.name:
            missing.append("full name")
        if not booking.email:
            missing.append("email")
        reply = await _reply(
            f"Still missing: {', '.join(missing)}. Ask only for the missing field(s).",
            booking,
            resuming_after_faq,
            slots_listing,
        )
        return {"booking": booking, "active_node": "booking", "messages": [AIMessage(content=reply)]}

    if booking.slot_id is None:
        reply = await _reply(
            "Name and email are collected. No slot chosen yet. Present the "
            "available slots listed above and ask the user to pick one.",
            booking,
            resuming_after_faq,
            slots_listing,
        )
        return {"booking": booking, "active_node": "booking", "messages": [AIMessage(content=reply)]}

    # A slot is chosen and not yet confirmed: attempt the actual booking via
    # the LangChain tool (atomic in the store; rejects a double-booked slot).
    service_type = booking.service_type or DEFAULT_SERVICE_TYPE
    tool_output = await book_slot.ainvoke(
        {
            "name": booking.name,
            "email": booking.email,
            "slot_id": booking.slot_id,
            "service_type": service_type,
        }
    )

    if "Booking confirmed" in tool_output and "Reference ID:" in tool_output:
        reference_id = tool_output.split("Reference ID:")[1].split(".")[0].strip()
        booking.status = "confirmed"
        booking.reference_id = reference_id
        booking.service_type = service_type
        confirmation = (
            f"Confirmed! Your {service_type} is scheduled for {booking.slot_label} "
            f"IST for {booking.name}. Reference ID: #{reference_id}."
        )
        return {
            "booking": booking,
            "active_node": "booking",
            "messages": [AIMessage(content=confirmation)],
        }

    # Slot vanished between selection and booking (e.g. double-booked just now).
    booking.slot_id = None
    booking.slot_label = None
    refreshed = await slot_store.list_available_slots()
    refreshed_listing = _format_slots_listing(refreshed)
    reply = await _reply(
        f"The chosen slot is no longer available ({tool_output}). Present the "
        "refreshed list of available slots above and ask the user to choose again.",
        booking,
        resuming_after_faq,
        refreshed_listing,
    )
    return {"booking": booking, "active_node": "booking", "messages": [AIMessage(content=reply)]}
