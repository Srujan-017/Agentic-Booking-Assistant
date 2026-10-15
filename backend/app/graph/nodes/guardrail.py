from __future__ import annotations

import re

from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel

from app.graph.llm import get_router_llm
from app.graph.prompts import GUARDRAIL_SYSTEM
from app.graph.state import AgentState

MAX_MESSAGE_CHARS = 2000

# Fast, cheap rule-based net for the obvious cases; the LLM check below catches
# subtler phrasing. Keeping both means a quota/outage on the LLM call still
# blocks the blatant attempts.
INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard (all |any )?(previous|prior|above) instructions",
    r"reveal (your |the )?system prompt",
    r"show (me )?(your |the )?(system|internal) prompt",
    r"you are now (in )?(developer|dan|jailbreak|unrestricted) mode",
    r"act as (an? )?unrestricted",
    r"pretend (you have no|there are no) (rules|restrictions|guidelines)",
    r"what (is|are) your (system|internal) (prompt|instructions)",
]
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

REFUSAL_REPLY = (
    "I can't help with that request. I can answer questions about the employee "
    "handbook or help you book an appointment — what would you like to do?"
)


class SafetyVerdict(BaseModel):
    safe: bool
    reason: str


def _matches_rule(text: str) -> bool:
    return any(p.search(text) for p in _COMPILED_PATTERNS)


async def guardrail_node(state: AgentState) -> dict:
    messages = state["messages"]
    last_user_text = ""
    for msg in reversed(messages):
        role = getattr(msg, "type", None) or (msg.get("role") if isinstance(msg, dict) else None)
        if role in ("human", "user"):
            last_user_text = msg.content if hasattr(msg, "content") else msg.get("content", "")
            break

    blocked = False
    if len(last_user_text) > MAX_MESSAGE_CHARS:
        blocked = True
    elif _matches_rule(last_user_text):
        blocked = True
    else:
        try:
            llm = get_router_llm().with_structured_output(SafetyVerdict)
            verdict: SafetyVerdict = await llm.ainvoke(
                [
                    SystemMessage(content=GUARDRAIL_SYSTEM),
                    {"role": "user", "content": f"Message: {last_user_text}"},
                ]
            )
            blocked = not verdict.safe
        except Exception:
            # If the safety classifier call itself fails, fail open on rules
            # already checked above rather than blocking legitimate traffic.
            blocked = False

    if blocked:
        return {
            "intent": "blocked",
            "active_node": "guardrail",
            "citations": [],
            "messages": [AIMessage(content=REFUSAL_REPLY)],
        }

    return {"active_node": "guardrail"}
