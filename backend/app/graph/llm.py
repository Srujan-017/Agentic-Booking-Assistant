from functools import lru_cache

from langchain_groq import ChatGroq

from app.config import get_settings


@lru_cache
def get_main_llm() -> ChatGroq:
    settings = get_settings()
    return ChatGroq(model=settings.llm_model, api_key=settings.groq_api_key, temperature=0.2)


@lru_cache
def get_router_llm() -> ChatGroq:
    settings = get_settings()
    return ChatGroq(model=settings.router_model, api_key=settings.groq_api_key, temperature=0)
