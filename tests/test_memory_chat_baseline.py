import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from persbot.core.db.sqlite import SQLiteDatabase
from persbot.core.memory.answer_showcase import EVIDENCE_INSTRUCTIONS, QUESTION
from persbot.core.memory.history import ConversationMemoryImporter, live_scope
from persbot.core.memory.initialize_showcase import initialize_showcase
from persbot.core.memory.service import HeLaMemoryService, MemoryConversationHooks


@pytest.mark.asyncio
async def test_installed_showcase_and_chat_share_exact_four_memories(tmp_path):
    db = SQLiteDatabase(str(tmp_path / "chat.db"))
    memory = HeLaMemoryService(tmp_path / "memory.db")
    try:
        scope = live_scope("webchat", "webchat", None, "alice")
        saved = await memory.remember(scope, "已有记忆保留")
        installed = await initialize_showcase(memory, db, "alice")
        graph = await memory.snapshot(scope)
        assert len(graph["nodes"]) == 6
        assert saved in {node["id"] for node in graph["nodes"]}
        assert len(installed["sessions"]) == 2
        for session in installed["sessions"]:
            assert (await ConversationMemoryImporter(memory, db).ingest("alice", session["id"]))["imported"] == 0
        assert await initialize_showcase(memory, db, "alice") == installed
        assert await memory.snapshot(scope) == graph
        assert not (await memory.snapshot(live_scope("webchat", "webchat", None, "bob")))["nodes"]

        memory._embed = AsyncMock(side_effect=AssertionError("Preset scores must remain preset"))
        pair = await memory.compare_fixed(scope, QUESTION)
        showcase = await memory.answer_showcase(scope)
        trace = await memory.recall_chat(scope, QUESTION)
        assert trace["results"] == pair["helamem"]["results"] == showcase["helamem"]["results"]
        assert [item["id"] for item in trace["results"]] == ["M89", "M20", "M15", "M40"]
        assert [item["id"] for item in pair["base"]["results"]] == ["M89", "M20", "M40", "M70"]
        assert trace["strategy"] == "paper_preset"
        assert trace["presentation"]["baseline_installed"]
        assert len(json.loads(trace["context"])) == 4
        assert "adoption support conference" in trace["context"]
        assert "参考答案" not in trace["context"]

        extras = {}
        event = SimpleNamespace(
            message_str=QUESTION, get_sender_id=lambda: "alice", get_sender_name=lambda: "alice",
            get_platform_name=lambda: "webchat", get_platform_id=lambda: "webchat", get_group_id=lambda: "",
            get_extra=extras.get, set_extra=lambda k, v: extras.__setitem__(k, v),
        )
        request = SimpleNamespace(prompt=QUESTION, system_prompt="Assistant", contexts=[{"role": "assistant", "content": "学校活动"}])
        await MemoryConversationHooks(memory).before(event, request)
        assert EVIDENCE_INSTRUCTIONS not in request.system_prompt
        assert request.system_prompt.startswith("Assistant\nHeLa-Mem recalled evidence")
        assert "用方括号引用" not in request.system_prompt
        assert "最多三句话" not in request.system_prompt
        assert "只根据下面 JSON" not in request.system_prompt
        assert "adoption support conference" in request.system_prompt
        assert extras["hela_memory_pending"]["trace"]["results"] == trace["results"]
        await memory.complete(scope, trace, "在收养支持会议上。[M89][M15]")
        assert memory._read(scope)["traces"][-1]["id"] == trace["id"]
    finally:
        await db.engine.dispose()


@pytest.mark.asyncio
async def test_non_case_chat_uses_actual_fixed_top_four(tmp_path):
    memory = HeLaMemoryService(tmp_path / "memory.db")
    for i in range(7):
        await memory.remember("alice", f"我的茶饮偏好 {i}")
    pair = await memory.compare_fixed("alice", "我喜欢什么茶？")
    trace = await memory.recall_chat("alice", "我喜欢什么茶？")
    assert trace["strategy"] == "fixed_k_vector_activation"
    assert len(trace["results"]) == 4
    assert trace["results"] == pair["helamem"]["results"]
    assert not trace["presentation"]
    assert not (await memory.recall_chat("bob", QUESTION))["results"]
