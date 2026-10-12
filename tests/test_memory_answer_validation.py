import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from persbot.core.memory.answer_showcase import career_case
from persbot.core.memory.answer_validation import CASES, VALIDATION_PROMPT, assess, resolve_case
from persbot.core.memory.service import HeLaMemoryService


def fixture_pair():
    pair = career_case()
    pair.pop("presentation")
    for side in ("base", "helamem"):
        pair[side]["strategy"] = "fixed_k_vector_activation"
        pair[side]["query"] = CASES["school-date"]["question"]
        for item in pair[side]["results"]:
            if item["id"] == "M15":
                item.update(id="abc123", origin={"title": "会话 3 · 归纳 1"}, content="On June 9, 2023, Caroline shared her school experience with Melanie.")
                item["paths"][0]["target"] = "abc123"
            else:
                item["content"] = "I talked about my school event last week."
    return pair


@pytest.mark.parametrize("text,side,status", [
    ("2023年6月9日。[abc123]", "helamem", "correct"),
    ("2023年6月9日。[abc123]", "base", "unsupported"),
    ("2023年6月9日。", "helamem", "unsupported"),
    ("可能在2023年6月9日。[abc123]", "helamem", "missing"),
    ("不是2023年6月9日。[abc123]", "helamem", "missing"),
    ("2023年5月8日。[abc123]", "helamem", "missing"),
    ("2023年6月9日。[abc123][fake]", "helamem", "unsupported"),
])
def test_correctness_requires_reference_and_recalled_evidence(text, side, status):
    pair = fixture_pair()
    result = assess(text, pair[side], resolve_case("school-date", pair))
    assert result["status"] == status
    assert result["text"] == text


def test_location_answer_cites_decisive_memory_and_requires_recalled_person_bridge():
    pair = career_case()
    case = resolve_case("paper-career", pair)
    text = "你第一次在收养支持会议上遇见了 Dr. Sarah。[M15]"
    assert assess(text, pair["helamem"], case)["status"] == "correct"
    without_person = pair["helamem"] | {
        "results": [item for item in pair["helamem"]["results"] if item["id"] != "M89"]
    }
    assert assess(text, without_person, case)["status"] == "unsupported"


@pytest.mark.asyncio
async def test_three_rounds_share_settings_save_raw_answers_and_do_not_write_graph(tmp_path):
    calls = []
    pair = fixture_pair()
    original = deepcopy(pair)

    async def generate(**kwargs):
        calls.append(kwargs)
        evidence = json.loads(kwargs["system_prompt"].split("\n", 1)[1])
        text = "2023年6月9日。[abc123]" if any(i["memory_id"] == "abc123" for i in evidence) else "无法确定具体日期。"
        return SimpleNamespace(completion_text=text)

    provider = SimpleNamespace(text_chat=generate, get_model=lambda: "test-model")
    service = HeLaMemoryService(tmp_path / "memory.db", SimpleNamespace(get_using_provider=lambda: provider))
    service.compare_fixed = AsyncMock(return_value=pair)
    service._update = Mock(side_effect=AssertionError("No memory writes"))
    result = await service.answer_validation("alice", "school-date", generation="model")
    verification = result["answer_comparison"]["verification"]
    assert verification["passed"] and verification["passed_runs"] == 3
    assert len(calls) == 9
    service.compare_fixed.assert_awaited_once_with("alice", CASES["school-date"]["question"], top_k=4)
    for index, call in enumerate(calls):
        prompt, data = call["system_prompt"].split("\n", 1)
        evidence = json.loads(data)
        assert prompt == VALIDATION_PROMPT
        assert call["temperature"] == 0 and call["contexts"] == []
        assert call["prompt"] == CASES["school-date"]["question"]
        assert CASES["school-date"]["reference"] not in call["system_prompt"]
        assert len(evidence) == (3 if index % 3 == 2 else 4)
        if index % 3 == 2:
            assert [r["memory_id"] for r in evidence] == [r["id"] for r in original["helamem"]["results"] if r["id"] != "abc123"]
    assert result["base"] == original["base"]
    assert result["helamem"] == original["helamem"]
    replay_service = HeLaMemoryService(tmp_path / "memory.db")
    replay = await replay_service.answer_validation("alice", "school-date")
    assert replay["answer_comparison"]["replayed"]
    assert replay["answer_comparison"]["verification"] == verification
    assert (await replay_service.answer_cases("alice"))[0]["passed"]
    assert not (await replay_service.answer_cases("bob"))[0]["saved"]
    with pytest.raises(ValueError, match="没有保存"):
        await replay_service.answer_validation("bob", "school-date")
    service._update.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["base_correct", "ablation_correct", "one_failed_round", "no_paths"])
async def test_no_claim_of_benefit_when_control_or_a_round_already_answers(tmp_path, failure):
    pair = fixture_pair()
    count = 0
    if failure == "no_paths":
        next(item for item in pair["helamem"]["results"] if item["id"] == "abc123")["paths"] = []

    async def generate(**kwargs):
        nonlocal count
        index = count
        count += 1
        correct = index % 3 == 1
        if failure == "base_correct" and index % 3 == 0:
            correct = True
        if failure == "ablation_correct" and index % 3 == 2:
            correct = True
        if failure == "one_failed_round" and index == 4:
            correct = False
        return SimpleNamespace(completion_text="2023年6月9日。[abc123]" if correct else "无法确定日期。")

    provider = SimpleNamespace(text_chat=generate, get_model=lambda: "test-model")
    service = HeLaMemoryService(tmp_path / "memory.db", SimpleNamespace(get_using_provider=lambda: provider))
    service.compare_fixed = AsyncMock(return_value=pair)
    result = await service.answer_validation("alice", "school-date", generation="model")
    assert not result["answer_comparison"]["verification"]["passed"]
    assert len(result["answer_comparison"]["verification"]["runs"]) == 3


@pytest.mark.asyncio
async def test_generation_failure_never_creates_fake_saved_success(tmp_path):
    provider = SimpleNamespace(text_chat=AsyncMock(return_value=SimpleNamespace(completion_text="")))
    service = HeLaMemoryService(tmp_path / "memory.db", SimpleNamespace(get_using_provider=lambda: provider))
    service.compare_fixed = AsyncMock(return_value=fixture_pair())
    with pytest.raises(ValueError, match="未返回回答"):
        await service.answer_validation("alice", "school-date", generation="model")
    assert not (await service.answer_cases("alice"))[0]["saved"]
