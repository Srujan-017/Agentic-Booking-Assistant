"""LangChain tools the booking graph node calls to execute transactional actions.

Kept thin on purpose: all real logic (atomic booking, slot seeding) lives in
app.services.slot_store so it can be unit-tested without an LLM in the loop.
"""

from __future__ import annotations

from langchain_core.tools import tool

from app.services import slot_store


@tool
async def get_available_slots() -> str:
    """List currently available appointment slots a user can book."""
    slots = await slot_store.list_available_slots()
    if not slots:
        return "No slots are currently available."
    lines = [f"{i + 1}. {s['label']} (slot_id={s['id']})" for i, s in enumerate(slots)]
    return "Available slots:\n" + "\n".join(lines)


@tool
async def book_slot(name: str, email: str, slot_id: int, service_type: str) -> str:
    """Book an appointment slot for a named person.

    Args:
        name: Full name of the person booking.
        email: Contact email of the person booking.
        slot_id: The numeric id of the slot to book, from get_available_slots.
        service_type: What the appointment is for, e.g. "Performance Review".
    """
    result = await slot_store.book_slot(
        name=name, email=email, slot_id=slot_id, service_type=service_type
    )
    if result.success:
        return (
            f"Booking confirmed. Reference ID: {result.reference_id}. "
            f"Slot: {result.slot_label}."
        )
    if result.error == "slot_already_booked":
        return "That slot was just booked by someone else. Please choose another."
    if result.error == "slot_not_found":
        return "That slot id does not exist. Please choose a valid slot."
    return f"Booking failed: {result.error}"
