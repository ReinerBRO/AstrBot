import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from quart import Quart

from persbot.core.memory.hebbian import LOCAL_ENCODER
from persbot.core.memory.history import live_scope
from persbot.core.memory.service import HeLaMemoryService, MemoryConversationHooks
from persbot.dashboard.routes.memory import MemoryRoute
from persbot.dashboard.routes.route import RouteContext


@pytest.fixture
def memory(tmp_path):
    return HeLaMemoryService(tmp_path / "memory.sqlite3")


@pytest.mark.asyncio
async def test_persistence_isolation_and_dedup(memory):
    nid = await memory.remember("alice", "我喜欢绿茶", event_key="turn1")
    again = await memory.remember("alice", "我喜欢绿茶", event_key="turn1")
    assert nid == again
    reopened = HeLaMemoryService(memory.path)
    assert len((await reopened.snapshot("alice"))["nodes"]) == 1
    assert not (await reopened.snapshot("bob"))["nodes"]
    assert not (await reopened.recall("bob", "绿茶"))["results"]


@pytest.mark.asyncio
async def test_dual_path_adds_provenance_without_mutation(memory):
    demo = await memory.seed_demo()
    before = await memory.snapshot(demo["scope"])
    pair = await memory.compare(demo["scope"], demo["query"], top_k=1)
    assert len(pair["base"]["results"]) == 1
    assert len(pair["helamem"]["results"]) == 2
    assert "职业选择有很大影响" in pair["base"]["results"][0]["content"]
    extra = pair["helamem"]["results"][1]
    assert extra["source"] == "hebbian"
    assert "领养支持大会" in extra["content"]
    assert extra["paths"][0]["boost"] > 0
    assert before == await memory.snapshot(demo["scope"])
    assert pair["base"]["revision"] == pair["helamem"]["revision"]
    for trace in pair.values():
        assert len(trace["context"]) == trace["context_chars"] <= trace["budget_chars"]
        assert len(json.loads(trace["context"])) == len(trace["results"])


@pytest.mark.asyncio
async def test_complete_reinforces_once_and_persists_trace(memory):
    demo = await memory.seed_demo()
    trace = await memory.recall(demo["scope"], demo["query"], top_k=1)
    await memory.complete(demo["scope"], trace, "Sarah，在领养支持大会。")
    graph = await memory.snapshot(demo["scope"])
    update = graph["traces"][0]["edge_updates"][0]
    assert update["after"] - update["before"] == pytest.approx(0.01)
    await memory.complete(demo["scope"], trace, "duplicate")
    after = await memory.snapshot(demo["scope"])
    assert len(after["traces"]) == 1
    assert after["edges"] == graph["edges"]
    assert after["nodes"] == graph["nodes"]
    with pytest.raises(ValueError, match="scope"):
        await memory.complete("bob", trace, "bad")


@pytest.mark.asyncio
async def test_consolidation_keeps_sources_and_is_honest_without_model(memory):
    a = await memory.remember("alice", "我每周二跑步")
    b = await memory.remember("alice", "我周四也跑步")
    result = await memory.consolidate("alice", [a, b])
    assert result["method"] == "extractive"
    graph = await memory.snapshot("alice")
    derived = next(n for n in graph["nodes"] if n["id"] == result["id"])
    assert derived["source_ids"] == [a, b]
    assert derived["kind"] == "semantic"
    assert derived["content"] == "我每周二跑步\n我周四也跑步"
    assert len(graph["edges"]) == 2
    with pytest.raises(ValueError):
        await memory.consolidate("bob", [a, b])


@pytest.mark.asyncio
async def test_model_comparison_only_changes_evidence(memory):
    provider = SimpleNamespace(
        text_chat=AsyncMock(
            return_value=SimpleNamespace(completion_text="真实返回测试")
        ),
        get_model=lambda: "test-model",
    )
    memory.context = SimpleNamespace(
        get_using_provider=lambda: provider, get_all_embedding_providers=lambda: []
    )
    demo = await memory.seed_demo()
    before = await memory.snapshot(demo["scope"])
    pair = await memory.answer_compare(demo["scope"], demo["query"], top_k=1)
    calls = provider.text_chat.call_args_list
    assert len(calls) == 2
    for call in calls:
        assert call.kwargs["prompt"] == demo["query"]
        assert call.kwargs["temperature"] == 0
        assert call.kwargs["max_tokens"] == 500
        assert call.kwargs["contexts"] == []
    assert calls[0].kwargs["system_prompt"] != calls[1].kwargs["system_prompt"]
    assert all(t["model"] == "test-model" for t in pair.values())
    assert before == await memory.snapshot(demo["scope"])


def make_event(sender="alice", conversation="chat1", mid="1", query="我喜欢绿茶"):
    extras = {}
    return SimpleNamespace(
        message_str=query,
        session_id=conversation,
        message_obj=SimpleNamespace(message_id=mid),
        get_sender_id=lambda: sender,
        get_sender_name=lambda: sender,
        get_platform_name=lambda: "webchat",
        get_platform_id=lambda: "webchat",
        get_group_id=lambda: "",
        get_extra=extras.get,
        set_extra=lambda k, v: extras.__setitem__(k, v),
    )


@pytest.mark.asyncio
async def test_chat_hooks_cross_session_and_disable(memory):
    hooks = MemoryConversationHooks(memory)
    event = make_event()
    req = SimpleNamespace(prompt=event.message_str, system_prompt="Assistant")
    await hooks.before(event, req)
    response = SimpleNamespace(
        is_chunk=False, role="assistant", tools_call_name=[], completion_text="记住了。"
    )
    await hooks.after(event, response)
    await hooks.after(event, response)
    scope = hooks.identity(event)[0]
    assert len((await memory.snapshot(scope))["nodes"]) == 1
    next_event = make_event(conversation="chat2", mid="2", query="我喜欢什么茶？")
    next_req = SimpleNamespace(prompt=next_event.message_str, system_prompt="Assistant")
    await hooks.before(next_event, next_req)
    assert "绿茶" in next_req.system_prompt
    assert "untrusted historical" in next_req.system_prompt
    bob = make_event(sender="bob", conversation="chat2", query="我喜欢什么茶？")
    bob_req = SimpleNamespace(prompt=bob.message_str, system_prompt="Assistant")
    await hooks.before(bob, bob_req)
    assert bob_req.system_prompt == "Assistant"
    await memory.configure(enabled=False, encoder=LOCAL_ENCODER)
    off = make_event(mid="3")
    await hooks.before(off, req)
    assert off.get_extra("hela_memory_pending") is None


@pytest.mark.asyncio
async def test_concurrent_writes_keep_all_nodes(memory):
    await asyncio.gather(*(memory.remember("alice", f"经历 {i}") for i in range(12)))
    assert len((await memory.snapshot("alice"))["nodes"]) == 12


@pytest.mark.asyncio
async def test_api_validation_and_real_graph(memory):
    app = Quart(__name__)
    MemoryRoute(
        RouteContext({}, app),
        SimpleNamespace(star_context=SimpleNamespace(memory_service=memory)),
    )
    client = app.test_client()
    invalid = await client.post(
        "/api/memory/add", json={"scope": "../other", "content": "text"}
    )
    assert invalid.status_code == 400
    invalid = await client.post(
        "/api/memory/compare", json={"scope": "alice", "query": "hi", "top_k": -1}
    )
    assert invalid.status_code == 400
    no_model = await client.post(
        "/api/memory/answer-compare", json={"scope": "alice", "query": "hi"}
    )
    assert no_model.status_code == 400
    demo = await memory.seed_demo()
    denied = await client.get("/api/memory/graph?scope=" + demo["scope"])
    assert denied.status_code == 400
    scope = live_scope("webchat", "webchat", None, "guest")
    await memory.remember(
        scope,
        "自己的聊天记忆",
        origin={"initialization_source": {"dataset": "private"}},
    )
    graph = await (await client.get("/api/memory/graph")).get_json()
    assert len(graph["data"]["nodes"]) == 1
    assert all("embedding" not in n for n in graph["data"]["nodes"])
    assert "initialization_source" not in graph["data"]["nodes"][0]["origin"]
    recall = await client.post("/api/memory/recall", json={"query": "聊天记忆"})
    assert recall.status_code == 200
    assert (await client.post("/api/memory/demo", json={})).status_code == 404
    assert (await client.post("/api/memory/atlas-demo", json={})).status_code == 404
    scopes = await (await client.get("/api/memory/scopes")).get_json()
    assert [s["scope"] for s in scopes["data"]] == [scope]
    assert (await client.get("/api/memory/locomo")).status_code == 404


@pytest.mark.asyncio
async def test_atlas_demo_is_isolated_idempotent_and_traceable(memory):
    await memory.remember("alice", "真实聊天里的记忆")
    demo = await memory.seed_atlas_demo()
    first = await memory.snapshot(demo["scope"])
    await memory.seed_atlas_demo()
    second = await memory.snapshot(demo["scope"])
    ids = {node["id"] for node in first["nodes"]}
    assert len(ids) == 24
    assert {node["id"] for node in second["nodes"]} == ids
    assert len((await memory.snapshot("alice"))["nodes"]) == 1
    assert {node["kind"] for node in first["nodes"]} == {
        "episodic",
        "semantic",
        "profile",
        "pattern",
    }
    for node in first["nodes"]:
        assert node["origin"]["method"] in {"demo", "demo_curated"}
        assert set(node["source_ids"]) <= ids
    assert all(
        edge["source"] in ids and edge["target"] in ids for edge in first["edges"]
    )


@pytest.mark.asyncio
async def test_context_budget_covers_actual_serialized_payload(memory):
    await memory.remember("alice", '绿茶"\\\n' * 200)
    trace = await memory.recall("alice", "绿茶", budget=300)
    assert trace["context_chars"] <= 300
    assert not trace["results"]


@pytest.mark.asyncio
async def test_existing_scope_keeps_encoder(memory):
    await memory.remember("alice", "绿茶")
    dense = SimpleNamespace(
        meta=lambda: SimpleNamespace(id="dense"),
        get_embedding=AsyncMock(return_value=[1.0, 0.0]),
    )
    memory.context = SimpleNamespace(
        get_all_embedding_providers=lambda: [dense], get_provider_by_id=lambda _: dense
    )
    await memory.configure(enabled=True, encoder="dense")
    await memory.remember("alice", "红茶")
    await memory.remember("bob", "咖啡")
    assert (await memory.snapshot("alice"))["encoder"] == LOCAL_ENCODER
    assert (await memory.snapshot("bob"))["encoder"] == "dense"
    assert dense.get_embedding.await_count == 1
