import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from persbot.core.memory.answer_showcase import QUESTION, assess_answer, career_case, scripted_case
from persbot.core.memory.service import HeLaMemoryService


def test_script_has_equal_top_four_and_explicitly_authored_provenance():
    pair = scripted_case()
    assert [r["embedding_rank"] for r in pair["base"]["results"]] == [1, 2, 3, 4]
    assert len(pair["helamem"]["results"]) == 4
    assert "M15" not in [r["id"] for r in pair["base"]["results"]]
    target = next(r for r in pair["helamem"]["results"] if r["id"] == "M15")
    assert target["cosine"] == 0.35
    assert target["score"] == pytest.approx(target["base_score"] + target["association_score"])
    assert target["selected_rank"] == 3
    assert pair["answer_comparison"]["mode"] == "scripted"
    assert pair["answer_comparison"]["base"]["status"] == "missing"
    assert pair["answer_comparison"]["helamem"]["status"] == "correct"
    nodes = pair["presentation"]["graph"]["nodes"]
    assert sum(n["origin"]["method"] == "paper_case" for n in nodes) == 2
    assert sum(n["origin"]["method"] == "showcase_background" for n in nodes) == 3


@pytest.mark.parametrize("text,side,status", [
    ("在收养支持会议上。[M89][M15]", "helamem", "correct"),
    ("在收养支持会议上。[M89][M15]", "base", "unsupported"),
    ("无法确定是不是在收养支持会议上。[M89][M15]", "helamem", "missing"),
    ("在收养支持会议上。", "helamem", "unsupported"),
    ("在图书馆。[M89][M15]", "helamem", "missing"),
    ("在收养支持会议上。[M89][M15][M999]", "helamem", "unsupported"),
])
def test_answer_judgement_does_not_force_a_positive_result(text, side, status):
    result = assess_answer(text, career_case()[side])
    assert result["text"] == text
    assert result["status"] == status
    assert "M999" not in result["citations"]


@pytest.mark.asyncio
async def test_model_gets_same_question_settings_and_only_each_sides_evidence(tmp_path):
    calls = []

    async def generate(**kwargs):
        calls.append(kwargs)
        if "Met Dr. Sarah" in kwargs["system_prompt"]:
            return SimpleNamespace(completion_text="在收养支持会议上遇见 Sarah，她影响了你的职业选择。[M15][M89]")
        return SimpleNamespace(completion_text="Sarah 影响了你的职业选择，但无法确定初次见面的地点。[M89]")

    provider = SimpleNamespace(text_chat=generate, get_model=lambda: "gpt-4o-mini")
    service = HeLaMemoryService(tmp_path / "memory.db", SimpleNamespace(get_using_provider=lambda: provider))
    service._update = Mock(side_effect=AssertionError("No live graph writes"))
    pair = await service.answer_showcase("alice", generation="model")
    assert len(calls) == 2
    left, right = calls
    assert left["prompt"] == right["prompt"] == QUESTION
    assert left["contexts"] == right["contexts"] == []
    assert left["temperature"] == right["temperature"] == 0
    prefix_a, data_a = left["system_prompt"].split("\n", 1)
    prefix_b, data_b = right["system_prompt"].split("\n", 1)
    assert prefix_a == prefix_b
    assert len(json.loads(data_a)) == len(json.loads(data_b)) == 4
    assert "adoption support conference" not in data_a
    assert "adoption support conference" in data_b
    assert "参考答案" not in left["system_prompt"] + right["system_prompt"]
    answers = pair["answer_comparison"]
    assert answers["mode"] == "model"
    assert answers["model"] == "gpt-4o-mini"
    assert answers["base"]["status"] == "missing"
    assert answers["helamem"]["status"] == "correct"
    service._update.assert_not_called()


@pytest.mark.asyncio
async def test_failed_generation_does_not_substitute_scripted_answers(tmp_path):
    provider = SimpleNamespace(text_chat=AsyncMock(return_value=SimpleNamespace(completion_text="")), get_model=lambda: "gpt-4o-mini")
    service = HeLaMemoryService(tmp_path / "memory.db", SimpleNamespace(get_using_provider=lambda: provider))
    with pytest.raises(ValueError, match="未返回回答"):
        await service.answer_showcase("alice", generation="model")


@pytest.mark.asyncio
async def test_script_does_not_need_model_or_modify_saved_memories(tmp_path):
    service = HeLaMemoryService(tmp_path / "memory.db")
    await service.remember("alice", "existing chat")
    before = service._read("alice")
    pair = await service.answer_showcase("alice")
    assert pair["answer_comparison"]["mode"] == "scripted"
    assert service._read("alice") == before
