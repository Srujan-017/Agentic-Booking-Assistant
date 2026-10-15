from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage

from app.graph.llm import get_main_llm
from app.graph.prompts import RAG_SYSTEM
from app.graph.state import AgentState, Citation
from app.rag.retriever import get_retriever


def _last_user_text(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        role = getattr(msg, "type", None)
        if role == "human":
            return msg.content
    return ""


async def rag_node(state: AgentState) -> dict:
    question = state.get("faq_question") or _last_user_text(state)

    retriever = get_retriever(k=4)
    docs = await retriever.ainvoke(question)

    context = "\n\n".join(
        f"[p.{d.metadata.get('page')}] {d.page_content}" for d in docs
    )
    citations: list[Citation] = [
        {
            "page": d.metadata.get("page", 0),
            "source": d.metadata.get("source", "Employee Handbook"),
            "snippet": d.page_content[:200],
        }
        for d in docs
    ]

    system = RAG_SYSTEM.format(context=context or "(no matching excerpts found)")
    llm = get_main_llm()
    response = await llm.ainvoke([SystemMessage(content=system), {"role": "user", "content": question}])

    return {
        "messages": [AIMessage(content=response.content)],
        "citations": citations,
        "active_node": "rag",
    }
