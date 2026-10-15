"""Opens the SQLite checkpointer with an explicit msgpack allowlist.

Without this, LangGraph's default serializer warns "Deserializing
unregistered type app.graph.state.BookingDraft from checkpoint. This will be
blocked in a future version" on every resumed thread, because BookingDraft is
a custom Pydantic model the serializer doesn't recognize out of the box.
Registering it here keeps checkpoint round-tripping working once that block
lands, instead of leaving a ticking time bomb for later.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.graph.state import BookingDraft

_SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[(BookingDraft.__module__, BookingDraft.__name__)]
)


@asynccontextmanager
async def open_checkpointer(db_path: str) -> AsyncIterator[AsyncSqliteSaver]:
    async with aiosqlite.connect(db_path) as conn:
        yield AsyncSqliteSaver(conn, serde=_SERDE)
