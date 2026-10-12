from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from quart import Quart, g

from persbot.core.db.sqlite import SQLiteDatabase
from persbot.core.memory.answer_showcase import QUESTION
from persbot.core.memory.hebbian import lexical_embedding
from persbot.core.memory.history import ConversationMemoryImporter, live_scope
from persbot.core.memory.initialize_demo import initialize_demo, load_demo
from persbot.core.memory.service import HeLaMemoryService
from persbot.dashboard.routes.memory import MemoryRoute
from persbot.dashboard.routes.route import RouteContext


def demo_service(tmp_path, db):
    provider = SimpleNamespace(
        get_model=lambda: "gpt-4o-mini",
        meta=lambda: SimpleNamespace(id="team-model"),
        client=SimpleNamespace(embeddings=object()),
        text_chat=AsyncMock(side_effect=AssertionError("Initialization must not generate answers")),
    )
    context = SimpleNamespace(
        get_using_provider=lambda: provider,
        get_db=lambda: db,
        get_all_embedding_providers=lambda: [],
    )
    service = HeLaMemoryService(tmp_path / "memory.db", context)
    service._embed_many = AsyncMock(side_effect=lambda texts, encoder: [lexical_embedding(text) for text in texts])
    return service


def test_portable_fixture_contains_only_public_initialization_records():
    bundle = load_demo()
    assert len(bundle["nodes"]) == 34
    assert sum(node["kind"] == "episodic" for node in bundle["nodes"].values()) == 29
    assert "2023" in bundle["nodes"]["2515138b14ec"]["content"]
    for node in bundle["nodes"].values():
        assert "embedding" not in node
        assert node["origin"]["dataset"] == "LoCoMo"
        assert not {"sender_id", "session_id", "message_ids", "initialization_source"} & node["origin"].keys()
        assert node["content"] != QUESTION
    for edge in bundle["edges"]:
        assert edge["source"] in bundle["nodes"] and edge["target"] in bundle["nodes"]


@pytest.mark.asyncio
async def test_empty_deployment_installs_both_cases_and_chat_then_retries_without_duplicates(tmp_path):
    db = SQLiteDatabase(str(tmp_path / "chat.db"))
    service = demo_service(tmp_path, db)
    try:
        result = await initialize_demo(service, db, "teammate")
        assert result["memories"] == 39 and result["turns"] == 34
        assert len(result["sessions"]) == 5
        assert result["encoder"] == "chat-embedding:team-model"
        settings = await service.settings()
        assert settings["enabled"] and settings["encoder"] == result["encoder"]
        graph = await service.snapshot(result["scope"])
        assert len(graph["nodes"]) == 39
        assert graph["baseline"]["id"] == "paper-career"
        assert len(graph["edges"]) == len(load_demo()["edges"]) + 1
        pair = await service.compare_fixed(result["scope"], QUESTION)
        assert {item["id"] for item in pair["base"]["results"]} == {"M89", "M20", "M40", "M70"}
        assert {item["id"] for item in pair["helamem"]["results"]} == {"M89", "M20", "M15", "M40"}
        assert (await service.recall_chat(result["scope"], QUESTION))["results"] == pair["helamem"]["results"]
        importer = ConversationMemoryImporter(service, db)
        assert sum([len(await importer.records(session["id"])) for session in result["sessions"]]) == 68
        for session in result["sessions"]:
            assert (await importer.ingest("teammate", session["id"]))["imported"] == 0
        assert not (await service.snapshot(live_scope("webchat", "webchat", None, "another-user")))["nodes"]
        new_id = await service.remember(result["scope"], "部署之后新聊的内容")
        before = await service.snapshot(result["scope"])
        service._embed_many.reset_mock()
        assert await initialize_demo(service, db, "teammate") == result
        assert await service.snapshot(result["scope"]) == before
        assert new_id in {node["id"] for node in before["nodes"]}
        service._embed_many.assert_not_awaited()
        service.context.get_using_provider().text_chat.assert_not_awaited()
    finally:
        await db.engine.dispose()


@pytest.mark.asyncio
async def test_initializer_rejects_missing_model_and_does_not_reindex_existing_memory(tmp_path):
    db = SQLiteDatabase(str(tmp_path / "chat.db"))
    service = demo_service(tmp_path, db)
    try:
        scope = live_scope("webchat", "webchat", None, "teammate")
        await service.remember(scope, "已有本地词面编码记忆")
        before = await service.snapshot(scope)
        with pytest.raises(ValueError, match="重建语义索引"):
            await initialize_demo(service, db, "teammate")
        assert await service.snapshot(scope) == before
        service.context.get_using_provider = lambda: None
        with pytest.raises(ValueError, match="gpt-4o-mini"):
            await initialize_demo(service, db, "teammate")
        assert await service.snapshot(scope) == before
    finally:
        await db.engine.dispose()


@pytest.mark.asyncio
async def test_demo_route_initializes_only_current_dashboard_owner(tmp_path):
    db = SQLiteDatabase(str(tmp_path / "chat.db"))
    service = demo_service(tmp_path, db)
    app = Quart(__name__)

    @app.before_request
    async def identify():
        g.username = "teammate"

    context = service.context
    context.memory_service = service
    MemoryRoute(RouteContext({}, app), SimpleNamespace(star_context=context))
    try:
        client = app.test_client()
        response = await client.post("/api/memory/initialize-demo", json={"scope": "someone-else"})
        assert response.status_code == 400
        response = await client.post("/api/memory/initialize-demo", json={})
        payload = await response.get_json()
        assert response.status_code == 200 and payload["status"] == "ok"
        assert payload["data"]["memories"] == 39
        assert payload["data"]["scope"] == live_scope("webchat", "webchat", None, "teammate")
    finally:
        await db.engine.dispose()
