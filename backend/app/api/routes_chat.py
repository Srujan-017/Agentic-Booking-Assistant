from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessageChunk
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import ChatRequest, ChatResponse, ThreadStateOut
from app.graph.output_guard import sanitize_reply
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
            # Two stream modes at once: "updates" fires once per node (any
            # node — guardrail, router, rag, ...) and drives the live node
            # badge/path trail; "messages" fires per LLM token and drives
            # the streamed text. Multi-mode astream yields (mode, payload)
            # tuples instead of the bare payload a single mode would give.
            async for mode, payload_chunk in graph.astream(
                {"messages": [{"role": "user", "content": payload.message}]},
                config=config,
                stream_mode=["updates", "messages"],
            ):
                if mode == "updates":
                    for node_name, node_output in payload_chunk.items():
                        yield {"event": "node", "data": json.dumps({"node": node_name})}
                        # Authoritative final text for each message this node
                        # produced. Needed as more than a nicety: a node can
                        # return a plain AIMessage with no LLM call behind it
                        # at all (e.g. booking's hardcoded confirmation line),
                        # which never generates a single "token" event — the
                        # client would otherwise drop that reply entirely.
                        for msg in node_output.get("messages", []) or []:
                            text = getattr(msg, "content", None)
                            if text:
                                yield {
                                    "event": "message",
                                    "data": json.dumps(
                                        {"node": node_name, "text": sanitize_reply(text)}
                                    ),
                                }
                    continue

                # mode == "messages": payload_chunk is (chunk, metadata).
                chunk, metadata = payload_chunk
                # "messages" mode emits two different things tagged with the
                # same node: incremental AIMessageChunk pieces during LLM
                # generation, AND the final, complete AIMessage a node
                # returns as part of its state update. Only the former is a
                # new token — the latter duplicates everything already
                # streamed, so it must be skipped or the client sees the
                # full answer appended a second time after the real stream.
                if not isinstance(chunk, AIMessageChunk):
                    continue
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

            # Output-side guardrail, checked on the actual persisted reply:
            # if a leak slipped through despite the input guardrail, don't
            # tell the client this turn succeeded normally.
            messages = values.get("messages", [])
            last_reply = messages[-1].content if messages else ""
            if sanitize_reply(last_reply) != last_reply:
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": "Response blocked by output guardrail."}),
                }
                return

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
