import pytest

from app.services import slot_store
from app.tools.booking_tools import book_slot, get_available_slots


@pytest.fixture
async def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "tools_app.sqlite")
    await slot_store.init_db(path)
    monkeypatch.setattr(slot_store, "default_db_path", lambda: path)
    return path


async def test_get_available_slots_tool_lists_slots(db_path):
    output = await get_available_slots.ainvoke({})
    assert "slot_id=" in output
    assert "Tomorrow" in output or "Friday" in output


async def test_book_slot_tool_confirms_booking(db_path):
    slots = await slot_store.list_available_slots(db_path)
    target = slots[0]

    output = await book_slot.ainvoke(
        {
            "name": "Alex Chen",
            "email": "alex.chen@example.com",
            "slot_id": target["id"],
            "service_type": "Performance Review",
        }
    )

    assert "Booking confirmed" in output
    assert "REV-" in output
