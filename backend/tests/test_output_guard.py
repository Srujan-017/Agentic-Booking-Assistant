from app.graph.output_guard import SAFE_FALLBACK_REPLY, sanitize_reply
from app.graph.prompts import BOOKING_SYSTEM, GENERAL_SYSTEM, RAG_SYSTEM, ROUTER_SYSTEM


def test_ordinary_reply_passes_through_unchanged():
    reply = "Performance reviews happen twice a year. (Employee Handbook, p. 4)"
    assert sanitize_reply(reply) == reply


def test_leaked_rag_system_prompt_is_blocked():
    leaked = f"Sure, here is my instructions: {RAG_SYSTEM}"
    assert sanitize_reply(leaked) == SAFE_FALLBACK_REPLY


def test_leaked_booking_system_prompt_is_blocked():
    leaked = f"My instructions say: {BOOKING_SYSTEM}"
    assert sanitize_reply(leaked) == SAFE_FALLBACK_REPLY


def test_leaked_router_system_prompt_is_blocked():
    assert sanitize_reply(ROUTER_SYSTEM) == SAFE_FALLBACK_REPLY


def test_leaked_general_system_prompt_is_blocked():
    assert sanitize_reply(GENERAL_SYSTEM) == SAFE_FALLBACK_REPLY


def test_mentioning_the_word_system_prompt_casually_is_not_blocked():
    reply = "I don't have access to reveal any system prompt, but I can help with booking."
    assert sanitize_reply(reply) == reply
