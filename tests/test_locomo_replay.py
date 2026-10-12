import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from persbot.core.memory.locomo import LocomoReplay
from persbot.core.memory.service import HeLaMemoryService


def make_dataset(path):
    conversation = {"speaker_a": "Alice", "speaker_b": "Bob"}
    for session in range(1, 4):
        conversation[f"session_{session}_date_time"] = f"day {session}"
        conversation[f"session_{session}"] = [
            {
                "dia_id": f"D{session}:{turn}",
                "speaker": "Alice" if turn % 2 else "Bob",
                "text": f"session {session}, utterance {turn}: tea and reading",
            }
            for turn in range(1, 5)
        ]
    path.write_text(
        json.dumps(
            [
                {
                    "sample_id": "test",
                    "conversation": conversation,
                    "qa": [
                        {
                            "question": "What did Alice mention?",
                            "evidence": ["D1:1"],
                            "answer": "FORBIDDEN_QA_ANSWER",
                        }
                    ],
                    "observation": "FORBIDDEN_PRECOMPUTED_OBSERVATION",
                }
            ]
        )
    )


@pytest.mark.asyncio
async def test_chronological_replay_provenance_no_answer_leak_and_resume(tmp_path):
    make_dataset(tmp_path / "locomo10.json")
    prompts = []

    async def respond(**kwargs):
        prompts.append(kwargs)
        if "Summarize" in kwargs["system_prompt"]:
            return SimpleNamespace(completion_text="依据本次会话整理的知识")
        return SimpleNamespace(
            completion_text=json.dumps(
                {"reply": "收到你的分享。", "title": "本轮茶与阅读"}
            )
        )

    provider = SimpleNamespace(
        text_chat=AsyncMock(side_effect=respond), get_model=lambda: "gpt-4o-mini"
    )
    context = SimpleNamespace(
        get_using_provider=lambda: provider, get_all_embedding_providers=lambda: []
    )
    memory = HeLaMemoryService(tmp_path / "memory.sqlite3", context)
    runner = LocomoReplay(memory)
    info = runner.dataset()
    assert info["total"] == 6
    await runner.start()
    await runner.task
    state = await runner.status()
    assert state["status"] == "complete"
    assert state["completed"] == 6
    assert state["model_calls"] == 9
    graph = await memory.snapshot(info["scope"])
    episodes = [node for node in graph["nodes"] if node["kind"] == "episodic"]
    assert [node["origin"]["dia_id"] for node in episodes] == [
        "D1:1",
        "D1:3",
        "D2:1",
        "D2:3",
        "D3:1",
        "D3:3",
    ]
    assert all(node["origin"]["source_text"] in node["content"] for node in episodes)
    assert all(node["origin"]["speaker"] == "Alice" for node in episodes)
    assert len(graph["traces"]) == 6
    assert not graph["traces"][0]["results"]
    serialized = json.dumps(prompts) + json.dumps(graph)
    assert "FORBIDDEN_QA_ANSWER" not in serialized
    assert "FORBIDDEN_PRECOMPUTED_OBSERVATION" not in serialized
    await runner.start()
    assert provider.text_chat.await_count == 9
    # Recreating the runner must not repeat completed model calls.
    await LocomoReplay(memory).start()
    assert provider.text_chat.await_count == 9


@pytest.mark.asyncio
async def test_interrupted_replay_keeps_completed_turns_and_accepts_plain_reply(
    tmp_path,
):
    make_dataset(tmp_path / "locomo10.json")
    count = 0

    async def respond(**kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("temporary provider failure")
        return SimpleNamespace(completion_text="模型的纯文本回复")

    provider = SimpleNamespace(
        text_chat=AsyncMock(side_effect=respond), get_model=lambda: "gpt-4o-mini"
    )
    memory = HeLaMemoryService(
        tmp_path / "memory.sqlite3",
        SimpleNamespace(
            get_using_provider=lambda: provider, get_all_embedding_providers=lambda: []
        ),
    )
    runner = LocomoReplay(memory)
    await runner.start()
    await runner.task
    assert (await runner.status())["status"] == "failed"
    first = await memory.snapshot(runner.dataset()["scope"])
    assert len(first["nodes"]) == 1
    await runner.start()
    await runner.task
    assert (await runner.status())["status"] == "complete"
    final = await memory.snapshot(runner.dataset()["scope"])
    assert final["nodes"][0]["id"] == first["nodes"][0]["id"]
    assert len([node for node in final["nodes"] if node["kind"] == "episodic"]) == 6
