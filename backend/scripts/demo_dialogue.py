"""Runs the exact Section 7 sample dialogue from the assessment end to end
against the compiled graph and prints a readable per-node trace, so it can be
captured as a verification artifact (docs/traces/).

Run with: python -m scripts.demo_dialogue
"""

from __future__ import annotations

import asyncio

from app.graph.builder import build_graph
from app.graph.checkpointer import open_checkpointer
from app.config import get_settings
from app.services import slot_store

TURNS = [
    "Hi, I need to book a 1-on-1 Performance Review session.",
    (
        "Alex Chen (alex.chen@example.com). Wait, before that, how often are "
        "performance reviews conducted according to the handbook?"
    ),
    None,  # filled in at runtime with a real available slot's label
]


async def main() -> None:
    settings = get_settings()
    await slot_store.init_db()

    checkpoint_path = str(settings.resolve("./demo_checkpoints.sqlite"))
    thread_id = "demo-dialogue"
    config = {"configurable": {"thread_id": thread_id}}

    available = await slot_store.list_available_slots()
    TURNS[2] = f"Let's go with {available[0]['label']}."

    print(f"=== Demo dialogue trace (thread_id={thread_id}) ===\n")

    async with open_checkpointer(checkpoint_path) as checkpointer:
        graph = build_graph(checkpointer)

        for i, user_text in enumerate(TURNS, start=1):
            print(f"--- Turn {i} ---")
            print(f"User: {user_text}")

            async for update in graph.astream(
                {"messages": [{"role": "user", "content": user_text}]},
                config=config,
                stream_mode="updates",
            ):
                for node_name, node_output in update.items():
                    print(f"  [node: {node_name}]")
                    for msg in node_output.get("messages", []):
                        content = getattr(msg, "content", None) or (
                            msg.get("content") if isinstance(msg, dict) else None
                        )
                        if content:
                            print(f"    -> {content}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
