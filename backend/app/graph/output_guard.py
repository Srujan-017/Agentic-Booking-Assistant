"""Output-side guardrail: a last line of defense checked right before a reply
leaves the server, independent of the input guardrail node. Even if a crafted
message somehow gets an LLM node to echo back part of its own system prompt,
this catches it before the client ever sees it.

Fingerprints are distinctive substrings unique to each node's own system
prompt in app.graph.prompts — not generic words, so this doesn't false-positive
on ordinary handbook/booking conversation.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("app.output_guard")

_SYSTEM_PROMPT_FINGERPRINTS = [
    "you are a safety classifier for a company's internal assistant",
    "you route a single user message to the right handler",
    "you answer questions using only the retrieved handbook excerpts",
    "you run the booking flow for appointment scheduling",
    "you are a friendly assistant for a company's employees",
    "extract any booking details present in the latest user message",
]

SAFE_FALLBACK_REPLY = (
    "I can't share that. I can answer questions about the employee handbook "
    "or help you book an appointment — what would you like to do?"
)


def sanitize_reply(text: str) -> str:
    lowered = text.lower()
    if any(fingerprint in lowered for fingerprint in _SYSTEM_PROMPT_FINGERPRINTS):
        logger.warning("Blocked an outgoing reply that appeared to leak system-prompt content.")
        return SAFE_FALLBACK_REPLY
    return text
