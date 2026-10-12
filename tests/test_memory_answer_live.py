import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from quart import Quart, g

from persbot.core.astr_main_agent_resources import CHATUI_SPECIAL_DEFAULT_PERSONA_PROMPT
from persbot.core.memory.answer_live import MEMORY_EVIDENCE_PREFIX, chat_persona
from persbot.core.memory.answer_validation import CASES, VALIDATION_PROMPT
from persbot.core.memory.history import live_scope
from persbot.core.memory.service import HeLaMemoryService
from persbot.dashboard.routes.memory import MemoryRoute
from persbot.dashboard.routes.route import RouteContext
from tests.test_memory_answer_validation import fixture_pair


def chat_context(provider, persona_id="default", personas=()):
    return SimpleNamespace(
        get_using_provider=lambda: provider,
        get_config=lambda: {"provider_settings": {"default_personality": persona_id}},
        persona_manager=SimpleNamespace(personas_v3=list(personas)),
    )


@pytest.mark.asyncio
async def test_typed_question_generates_fresh_answers_without_replaying_saved_validation(tmp_path):
    calls = []

    async def generate(**kwargs):
        calls.append(kwargs)
        evidence = json.loads(kwargs["system_prompt"].split(MEMORY_EVIDENCE_PREFIX)[1])
        text = "2023年6月9日。" if any("June 9" in i["text"] for i in evidence) else "是在上周。"
        return SimpleNamespace(completion_text=text)

    provider = SimpleNamespace(text_chat=generate, get_model=lambda: "gpt-4o-mini")
    service = HeLaMemoryService(tmp_path / "memory.db", chat_context(provider))
    pair = fixture_pair()
    service.compare_fixed = AsyncMock(side_effect=lambda *args, **kwargs: deepcopy(pair))
    service.answer_validation = AsyncMock(side_effect=AssertionError("Never replay saved cases"))
    service._update = Mock(side_effect=AssertionError("Never rewrite memories"))
    query = CASES["school-date"]["question"]
    for _ in range(2):
        result = await service.answer_fixed("alice", query)
        answers = result["answer_comparison"]
        assert answers["live"] and answers["question"] == query
        assert answers["base"]["text"] == "是在上周。"
        assert answers["helamem"]["text"] == "2023年6月9日。"
        assert all(answers[side]["status"] == "ungraded" for side in ("base", "helamem"))
        assert "verification" not in answers and "reference_answer" not in answers
        assert "replayed" not in answers
        assert result["base"] == pair["base"]
        assert result["helamem"] == pair["helamem"]
    assert len(calls) == 4
    for call in calls:
        prompt, evidence = call["system_prompt"].split(MEMORY_EVIDENCE_PREFIX)
        assert prompt == CHATUI_SPECIAL_DEFAULT_PERSONA_PROMPT
        memories = json.loads(evidence)
        assert len(memories) == 4
        assert all(set(item) == {"kind", "text"} for item in memories)
        assert VALIDATION_PROMPT not in call["system_prompt"]
        assert "memory_id" not in call["system_prompt"]
        assert "无法确定" not in call["system_prompt"]
        assert "M15" not in call["system_prompt"]
        assert call["prompt"] == query
        assert call["temperature"] == 0 and call["contexts"] == []
    service.answer_validation.assert_not_awaited()
    service._update.assert_not_called()


@pytest.mark.asyncio
async def test_arbitrary_question_is_answered_live_without_inventing_a_correctness_label(tmp_path):
    provider = SimpleNamespace(
        text_chat=AsyncMock(return_value=SimpleNamespace(completion_text="当前回答。[M89]")),
        get_model=lambda: "model",
    )
    service = HeLaMemoryService(tmp_path / "memory.db", chat_context(provider))
    service.compare_fixed = AsyncMock(return_value=fixture_pair())
    result = await service.answer_fixed("alice", "我之前提到过什么？", top_k=3)
    service.compare_fixed.assert_awaited_once_with("alice", "我之前提到过什么？", top_k=3)
    assert all(result["answer_comparison"][side]["status"] == "ungraded" for side in ("base", "helamem"))
    assert result["answer_comparison"]["base"]["text"] == "当前回答。[M89]"


@pytest.mark.asyncio
async def test_live_model_failure_does_not_fall_back_to_a_script(tmp_path):
    provider = SimpleNamespace(text_chat=AsyncMock(return_value=SimpleNamespace(completion_text="")))
    service = HeLaMemoryService(tmp_path / "memory.db", chat_context(provider))
    service.compare_fixed = AsyncMock(return_value=fixture_pair())
    service.answer_validation = AsyncMock(side_effect=AssertionError("No cached fallback"))
    with pytest.raises(ValueError, match="未返回回答"):
        await service.answer_fixed("alice", CASES["school-date"]["question"])
    service.answer_validation.assert_not_awaited()


@pytest.mark.asyncio
async def test_both_sides_use_configured_chat_persona_and_begin_dialogs(tmp_path):
    persona = {
        "name": "personal",
        "prompt": "保持原有的对话风格。",
        "_begin_dialogs_processed": [{"role": "user", "content": "你好"}],
    }
    provider = SimpleNamespace(
        text_chat=AsyncMock(return_value=SimpleNamespace(completion_text="自然回答。")),
        get_model=lambda: "model",
    )
    service = HeLaMemoryService(tmp_path / "memory.db", chat_context(provider, "personal", [persona]))
    service.compare_fixed = AsyncMock(return_value=fixture_pair())
    result = await service.answer_fixed("alice", CASES["school-date"]["question"])
    for call in provider.text_chat.await_args_list:
        assert call.kwargs["system_prompt"].split(MEMORY_EVIDENCE_PREFIX)[0] == "\n# Persona Instructions\n\n保持原有的对话风格。\n"
        assert call.kwargs["contexts"] == persona["_begin_dialogs_processed"]
        assert call.kwargs["contexts"] is not persona["_begin_dialogs_processed"]
    assert provider.text_chat.await_args_list[0].kwargs["contexts"] is not provider.text_chat.await_args_list[1].kwargs["contexts"]
    assert result["answer_comparison"]["helamem"]["text"] == "自然回答。"


def test_disabled_persona_is_not_replaced_by_validation_or_default_persona():
    assert chat_persona(chat_context(None, "[%None]")) == ("", [])


@pytest.mark.asyncio
async def test_live_route_uses_current_owner_and_equal_top_four():
    app = Quart(__name__)
    service = SimpleNamespace(answer_fixed=AsyncMock(return_value={"live": True}))

    @app.before_request
    async def identify():
        g.username = "alice"

    MemoryRoute(RouteContext({}, app), SimpleNamespace(star_context=SimpleNamespace(memory_service=service)))
    client = app.test_client()
    response = await client.post("/api/memory/answer-fixed", json={"query": "现场输入"})
    assert response.status_code == 200
    service.answer_fixed.assert_awaited_once_with(live_scope("webchat", "webchat", None, "alice"), "现场输入", top_k=4)
    response = await client.post("/api/memory/answer-fixed", json={"query": "现场输入", "scope": "bob"})
    assert response.status_code == 400
    assert service.answer_fixed.await_count == 1
