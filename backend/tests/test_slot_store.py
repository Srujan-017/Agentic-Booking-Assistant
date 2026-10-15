import pytest

from app.services import slot_store


@pytest.fixture
async def db_path(tmp_path):
    path = str(tmp_path / "test_app.sqlite")
    await slot_store.init_db(path)
    return path


async def test_seeds_at_least_minimum_upcoming_slots(db_path):
    slots = await slot_store.list_available_slots(db_path)
    assert len(slots) >= slot_store.MIN_UPCOMING_SLOTS


async def test_seeded_labels_look_right(db_path):
    # Not hardcoding "Friday": when "today" happens to be a Thursday, the
    # seeded Friday slot IS tomorrow, so the day-name prefix legitimately
    # varies by the date the test runs on. Check structure, not a fixed day.
    slots = await slot_store.list_available_slots(db_path)
    labels = [s["label"] for s in slots]
    assert any(label.startswith("Tomorrow") for label in labels)
    distinct_dates = {s["start_iso"][:10] for s in slots}
    assert len(distinct_dates) >= 3, "seeded slots should span multiple distinct days"


async def test_init_db_is_idempotent_and_future_safe(db_path):
    before = await slot_store.list_available_slots(db_path)
    await slot_store.init_db(db_path)
    after = await slot_store.list_available_slots(db_path)
    assert len(before) == len(after)


async def test_book_slot_succeeds_and_returns_reference_id(db_path):
    slots = await slot_store.list_available_slots(db_path)
    target = slots[0]

    result = await slot_store.book_slot(
        name="Alex Chen",
        email="alex.chen@example.com",
        slot_id=target["id"],
        service_type="Performance Review",
        db_path=db_path,
    )

    assert result.success
    assert result.reference_id.startswith("REV-")
    assert len(result.reference_id) == 8

    remaining = await slot_store.list_available_slots(db_path)
    assert target["id"] not in [s["id"] for s in remaining]


async def test_double_booking_the_same_slot_is_rejected(db_path):
    slots = await slot_store.list_available_slots(db_path)
    target = slots[0]

    first = await slot_store.book_slot(
        name="Alex Chen",
        email="alex.chen@example.com",
        slot_id=target["id"],
        service_type="Performance Review",
        db_path=db_path,
    )
    second = await slot_store.book_slot(
        name="Jordan Lee",
        email="jordan.lee@example.com",
        slot_id=target["id"],
        service_type="Performance Review",
        db_path=db_path,
    )

    assert first.success
    assert not second.success
    assert second.error == "slot_already_booked"


async def test_booking_unknown_slot_fails_cleanly(db_path):
    result = await slot_store.book_slot(
        name="Alex Chen",
        email="alex.chen@example.com",
        slot_id=999999,
        service_type="Performance Review",
        db_path=db_path,
    )
    assert not result.success
    assert result.error == "slot_not_found"


async def test_list_bookings_reflects_confirmed_booking(db_path):
    slots = await slot_store.list_available_slots(db_path)
    target = slots[0]
    result = await slot_store.book_slot(
        name="Alex Chen",
        email="alex.chen@example.com",
        slot_id=target["id"],
        service_type="Performance Review",
        db_path=db_path,
    )

    bookings = await slot_store.list_bookings(db_path)
    assert any(b["reference_id"] == result.reference_id for b in bookings)
