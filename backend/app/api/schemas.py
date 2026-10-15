from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CitationOut(BaseModel):
    page: int
    source: str
    snippet: str


class BookingOut(BaseModel):
    service_type: str | None = None
    name: str | None = None
    email: str | None = None
    slot_id: int | None = None
    slot_label: str | None = None
    status: Literal["idle", "collecting", "confirmed"] = "idle"
    reference_id: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    new_messages: list[MessageOut]
    active_node: str
    citations: list[CitationOut]
    booking: BookingOut


class ThreadStateOut(BaseModel):
    thread_id: str
    messages: list[MessageOut]
    booking: BookingOut
    citations: list[CitationOut]


class SlotOut(BaseModel):
    id: int
    label: str
    start_iso: str


class BookingRecordOut(BaseModel):
    reference_id: str
    name: str
    email: str
    service_type: str
    slot_label: str
    start_iso: str
    created_at: str


class HealthOut(BaseModel):
    status: str
    llm_key_configured: bool
    vector_store_doc_count: int


class ErrorOut(BaseModel):
    error: str
    detail: str
