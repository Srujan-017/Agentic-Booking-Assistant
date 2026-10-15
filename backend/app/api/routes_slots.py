from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import BookingRecordOut, SlotOut
from app.services import slot_store

router = APIRouter(tags=["slots"])


@router.get("/slots", response_model=list[SlotOut])
async def list_slots() -> list[dict]:
    return await slot_store.list_available_slots()


@router.get("/bookings", response_model=list[BookingRecordOut])
async def list_bookings() -> list[dict]:
    return await slot_store.list_bookings()
