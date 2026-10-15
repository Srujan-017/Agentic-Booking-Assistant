from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager

import groq
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_chat import router as chat_router
from app.api.routes_slots import router as slots_router
from app.api.schemas import HealthOut
from app.config import get_settings
from app.graph.builder import build_graph
from app.graph.checkpointer import open_checkpointer
from app.rag.retriever import vectorstore_doc_count
from app.services import slot_store

logger = logging.getLogger("app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await slot_store.init_db()
    if vectorstore_doc_count() == 0:
        logger.warning(
            "Vector store is empty. Run `python -m app.rag.ingest` before asking "
            "handbook questions."
        )

    stack = AsyncExitStack()
    checkpoint_path = str(settings.resolve(settings.checkpoint_db))
    checkpointer = await stack.enter_async_context(open_checkpointer(checkpoint_path))
    app.state.graph = build_graph(checkpointer)

    try:
        yield
    finally:
        await stack.aclose()


app = FastAPI(title="Agentic Booking & Policy Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(slots_router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": exc.errors()[0]["msg"] if exc.errors() else "Invalid request"},
    )


@app.exception_handler(groq.RateLimitError)
async def rate_limit_handler(request: Request, exc: groq.RateLimitError):
    return JSONResponse(
        status_code=503,
        content={"error": "rate_limited", "detail": "The LLM provider is rate-limiting requests. Please retry shortly."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "Something went wrong. Please try again."},
    )


@app.get("/api/health", response_model=HealthOut)
async def health() -> dict:
    return {
        "status": "ok",
        "llm_key_configured": bool(settings.groq_api_key),
        "vector_store_doc_count": vectorstore_doc_count(),
    }
