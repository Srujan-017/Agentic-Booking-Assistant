"""Async SQLite-backed store for appointment slots and bookings.

Slots are seeded relative to "now" in the configured timezone so labels
such as "Tomorrow 11:00 AM" never point to the past. Booking a slot is
atomic: a conditional UPDATE guarantees two concurrent requests can't
both win the same slot.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import aiosqlite

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_iso TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    is_booked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bookings (
    reference_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    slot_id INTEGER NOT NULL,
    service_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (slot_id) REFERENCES slots(id)
);
"""

MIN_UPCOMING_SLOTS = 3


class SlotStoreError(Exception):
    """Raised for programmer-error-style misuse; booking failures return a result dict instead."""


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def _now() -> datetime:
    return datetime.now(_tz())


def default_db_path() -> str:
    settings = get_settings()
    return str(settings.resolve(settings.app_db))


def _format_label(dt: datetime, now: datetime) -> str:
    if dt.date() == now.date():
        prefix = "Today"
    elif dt.date() == (now + timedelta(days=1)).date():
        prefix = "Tomorrow"
    else:
        prefix = dt.strftime("%A")

    time_str = dt.strftime("%I:%M %p")
    if time_str.startswith("0"):
        time_str = time_str[1:]
    return f"{prefix} {time_str}"


def _next_weekday(start: date, weekday: int) -> date:
    """weekday: Monday=0 ... Sunday=6. Returns the next such date after `start`."""
    days_ahead = (weekday - start.weekday()) % 7
    days_ahead = days_ahead or 7
    return start + timedelta(days=days_ahead)


def _candidate_datetimes(now: datetime) -> list[datetime]:
    tz = now.tzinfo
    today = now.date()
    friday = _next_weekday(today, 4)
    raw: list[tuple[date, time]] = [
        (today + timedelta(days=1), time(11, 0)),
        (today + timedelta(days=1), time(15, 0)),
        (today + timedelta(days=2), time(10, 0)),
        (today + timedelta(days=3), time(14, 30)),
        (friday, time(10, 30)),
        (friday + timedelta(days=3), time(11, 0)),
    ]
    return [datetime.combine(d, t, tzinfo=tz) for d, t in raw]


@dataclass
class BookingResult:
    success: bool
    reference_id: str | None = None
    slot_label: str | None = None
    error: str | None = None


def _open(db_path: str) -> aiosqlite.Connection:
    """Return an unawaited aiosqlite Connection for use with `async with`.

    aiosqlite.connect() returns a Connection that is itself awaitable; await
    (directly or via `async with`) is what starts its worker thread. Only
    enter it once per connection, via `async with`, not an eager `await`
    followed by a second `async with`.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return aiosqlite.connect(db_path)


async def init_db(db_path: str | None = None) -> None:
    db_path = db_path or default_db_path()
    now = _now()

    async with _open(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.executescript(SCHEMA)
        await conn.commit()

        # Drop unbooked slots that are now in the past so the list stays fresh.
        await conn.execute(
            "DELETE FROM slots WHERE is_booked = 0 AND start_iso < ?", (now.isoformat(),)
        )
        await conn.commit()

        cur = await conn.execute(
            "SELECT COUNT(*) AS n FROM slots WHERE is_booked = 0 AND start_iso >= ?",
            (now.isoformat(),),
        )
        row = await cur.fetchone()
        upcoming = row["n"] if row else 0

        if upcoming < MIN_UPCOMING_SLOTS:
            existing = {
                r["start_iso"]
                for r in await (await conn.execute("SELECT start_iso FROM slots")).fetchall()
            }
            for dt in _candidate_datetimes(now):
                if dt.isoformat() in existing:
                    continue
                await conn.execute(
                    "INSERT INTO slots (start_iso, label, is_booked) VALUES (?, ?, 0)",
                    (dt.isoformat(), _format_label(dt, now)),
                )
            await conn.commit()


async def list_available_slots(db_path: str | None = None) -> list[dict]:
    db_path = db_path or default_db_path()
    now = _now()
    async with _open(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT id, start_iso, label FROM slots "
            "WHERE is_booked = 0 AND start_iso >= ? ORDER BY start_iso ASC",
            (now.isoformat(),),
        )
        rows = await cur.fetchall()
        return [{"id": r["id"], "start_iso": r["start_iso"], "label": r["label"]} for r in rows]


async def get_slot(slot_id: int, db_path: str | None = None) -> dict | None:
    db_path = db_path or default_db_path()
    async with _open(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def _unique_reference_id(conn: aiosqlite.Connection) -> str:
    for _ in range(50):
        candidate = f"REV-{random.randint(1000, 9999)}"
        cur = await conn.execute(
            "SELECT 1 FROM bookings WHERE reference_id = ?", (candidate,)
        )
        if not await cur.fetchone():
            return candidate
    raise SlotStoreError("could not generate a unique reference id")


async def book_slot(
    *,
    name: str,
    email: str,
    slot_id: int,
    service_type: str,
    db_path: str | None = None,
) -> BookingResult:
    db_path = db_path or default_db_path()
    async with _open(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
        slot = await cur.fetchone()
        if not slot:
            return BookingResult(success=False, error="slot_not_found")

        update_cur = await conn.execute(
            "UPDATE slots SET is_booked = 1 WHERE id = ? AND is_booked = 0", (slot_id,)
        )
        if update_cur.rowcount == 0:
            await conn.rollback()
            return BookingResult(success=False, error="slot_already_booked")

        reference_id = await _unique_reference_id(conn)
        await conn.execute(
            "INSERT INTO bookings (reference_id, name, email, slot_id, service_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (reference_id, name, email, slot_id, service_type, _now().isoformat()),
        )
        await conn.commit()
        return BookingResult(success=True, reference_id=reference_id, slot_label=slot["label"])


async def list_bookings(db_path: str | None = None) -> list[dict]:
    db_path = db_path or default_db_path()
    async with _open(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT b.reference_id, b.name, b.email, b.service_type, b.created_at, "
            "s.label AS slot_label, s.start_iso "
            "FROM bookings b JOIN slots s ON s.id = b.slot_id "
            "ORDER BY b.created_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
