import pytest
from httpx import ASGITransport, AsyncClient

from app.graph.builder import build_graph
from app.graph.checkpointer import open_checkpointer
from app.main import app
from app.services import slot_store


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "api_app.sqlite")
    await slot_store.init_db(db_path)
    monkeypatch.setattr(slot_store, "default_db_path", lambda: db_path)

    checkpoint_path = str(tmp_path / "api_checkpoints.sqlite")
    async with open_checkpointer(checkpoint_path) as checkpointer:
        app.state.graph = build_graph(checkpointer)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm_key_configured"] is True
    assert body["vector_store_doc_count"] > 0


async def test_list_slots(client):
    r = await client.get("/api/slots")
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) >= 3
    assert {"id", "label", "start_iso"} <= slots[0].keys()


async def test_list_bookings_starts_empty(client):
    r = await client.get("/api/bookings")
    assert r.status_code == 200
    assert r.json() == []


async def test_chat_generates_thread_id_when_omitted(client):
    r = await client.post("/api/chat", json={"message": "Hi there"})
    assert r.status_code == 200
    body = r.json()
    assert body["thread_id"]
    assert body["reply"]
    assert body["booking"]["status"] == "idle"


async def test_chat_rejects_empty_message(client):
    r = await client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"


async def test_chat_rejects_oversized_message(client):
    r = await client.post("/api/chat", json={"message": "x" * 2001})
    assert r.status_code == 422


async def test_thread_state_404_for_unknown_thread(client):
    r = await client.get("/api/threads/does-not-exist")
    assert r.status_code == 404


async def test_full_booking_flow_persists_and_is_readable(client):
    thread_id = "api-flow-thread"

    r1 = await client.post(
        "/api/chat",
        json={"thread_id": thread_id, "message": "I'd like to book a Performance Review."},
    )
    assert r1.status_code == 200
    assert r1.json()["booking"]["status"] == "collecting"

    r2 = await client.post(
        "/api/chat",
        json={"thread_id": thread_id, "message": "Priya Rao, priya.rao@example.com"},
    )
    assert r2.status_code == 200
    booking2 = r2.json()["booking"]
    assert booking2["name"] and "rao" in booking2["name"].lower()
    assert booking2["email"] == "priya.rao@example.com"

    slots = (await client.get("/api/slots")).json()
    first_label = slots[0]["label"]
    r3 = await client.post(
        "/api/chat",
        json={"thread_id": thread_id, "message": f"I'll take {first_label}."},
    )
    assert r3.status_code == 200
    booking3 = r3.json()["booking"]
    assert booking3["status"] == "confirmed"
    assert booking3["reference_id"].startswith("REV-")

    # GET /api/threads/{id} reflects the same conversation and booking state.
    thread_state = (await client.get(f"/api/threads/{thread_id}")).json()
    assert thread_state["thread_id"] == thread_id
    assert thread_state["booking"]["status"] == "confirmed"
    assert len(thread_state["messages"]) >= 6  # 3 user + at least 3 assistant

    # The confirmed booking now shows up in /api/bookings.
    bookings = (await client.get("/api/bookings")).json()
    assert any(b["reference_id"] == booking3["reference_id"] for b in bookings)


async def test_chat_stream_emits_done_event(client):
    import json

    events: dict[str, list[str]] = {}
    async with client.stream(
        "POST", "/api/chat/stream", json={"message": "Hi, what can you help with?"}
    ) as response:
        assert response.status_code == 200
        current_event = None
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current_event:
                events.setdefault(current_event, []).append(line.split(":", 1)[1].strip())

    assert "done" in events
    done_payload = json.loads(events["done"][0])
    assert done_payload["thread_id"]
    assert "token" in events
    assert "".join(json.loads(t)["text"] for t in events["token"])

    # The node-badge trail: every node the graph passed through this turn,
    # in order, including ones that never stream text (guardrail, router).
    assert "node" in events
    node_names = [json.loads(n)["node"] for n in events["node"]]
    assert node_names[0] == "guardrail"
    assert "router" in node_names


async def test_chat_stream_delivers_a_reply_with_no_llm_call_behind_it(client):
    """The booking confirmation line is a hardcoded AIMessage, not an LLM
    call, so it produces no "token" events at all. Only the "message" event
    (the node's authoritative final text) carries it — if that event were
    missing, this reply would be silently dropped by any client that only
    builds bubbles from "token" events, with no error anywhere."""
    import json

    thread_id = "stream-confirmation-thread"
    await client.post(
        "/api/chat", json={"thread_id": thread_id, "message": "Book me a Performance Review."}
    )
    await client.post(
        "/api/chat",
        json={"thread_id": thread_id, "message": "Priya Rao, priya.rao@example.com"},
    )
    slots = (await client.get("/api/slots")).json()
    first_label = slots[0]["label"]

    events: dict[str, list[str]] = {}
    async with client.stream(
        "POST", "/api/chat/stream", json={"thread_id": thread_id, "message": f"{first_label}, please."}
    ) as response:
        current_event = None
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and current_event:
                events.setdefault(current_event, []).append(line.split(":", 1)[1].strip())

    assert "message" in events
    booking_messages = [
        json.loads(m) for m in events["message"] if json.loads(m)["node"] == "booking"
    ]
    assert any("Confirmed" in m["text"] and "REV-" in m["text"] for m in booking_messages)
