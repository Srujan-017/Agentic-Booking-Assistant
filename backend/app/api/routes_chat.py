from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import ChatRequest, ChatResponse, ThreadStateOut
from app.services.chat_service import get_thread_state, run_chat

router = APIRouter(tags=["chat"])


def _graph(request: Request) -> Any:
    return request.app.state.graph


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> dict:
    thread_id = payload.thread_id or str(uuid.uuid4())
    return await run_chat(_graph(request), thread_id, payload.message)


@router.get("/threads/{thread_id}", response_model=ThreadStateOut)
async def get_thread(request: Request, thread_id: str) -> dict:
    state = await get_thread_state(_graph(request), thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown thread_id '{thread_id}'")
    return state


@router.post("/chat/stream")
async def chat_stream(request: Request, payload: ChatRequest):
    graph = _graph(request)
    thread_id = payload.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        try:
            async for chunk, metadata in graph.astream(
                {"messages": [{"role": "user", "content": payload.message}]},
                config=config,
                stream_mode="messages",
            ):
                # Only stream tokens from user-facing answer nodes; the
                # router/extraction LLM calls use structured output (no
                # streamable text) and shouldn't leak partial JSON anyway.
                node_name = metadata.get("langgraph_node")
                if node_name not in ("rag", "booking", "general"):
                    continue
                text = getattr(chunk, "content", "")
                if text:
                    yield {"event": "token", "data": json.dumps({"node": node_name, "text": text})}

            final_state = await graph.aget_state(config)
            values = final_state.values
            yield {
                "event": "citations",
                "data": json.dumps(values.get("citations", [])),
            }
            booking = values.get("booking")
            yield {
                "event": "booking",
                "data": (booking or {}).model_dump_json() if booking else "{}",
            }
            yield {"event": "done", "data": json.dumps({"thread_id": thread_id})}
        except Exception as exc:  # noqa: BLE001 — must reach the client as an SSE error event
            yield {"event": "error", "data": json.dumps({"detail": str(exc)})}

    return EventSourceResponse(event_generator())
