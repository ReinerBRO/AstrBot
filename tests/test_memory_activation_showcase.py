from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from persbot.core.memory.hebbian import retrieve
from persbot.core.memory.service import HeLaMemoryService


def test_activation_exposes_real_similarity_ranks_paths_and_count_control():
    nodes = {}
    for nid, vector in [("a", [1, 0, 0]), ("b", [0.8, 0.6, 0]), ("c", [0, 0, 1])]:
        nodes[nid] = {
            "id": nid,
            "content": nid,
            "embedding": vector,
            "kind": "semantic",
            "keywords": [],
            "created_at": 0,
            "origin": {},
            "source_ids": [],
        }
    graph = {
        "nodes": nodes,
        "edges": [
            {
                "source": "a",
                "target": "c",
                "weight": 0.8,
                "reason": "co_retrieval",
                "reinforcements": 3,
            }
        ],
        "revision": 7,
    }
    off = retrieve(graph, "question", [1, 0, 0], associative=False, top_k=1)
    on = retrieve(graph, "question", [1, 0, 0], associative=True, top_k=1)
    assert [item["id"] for item in off["results"]] == ["a"]
    assert [item["id"] for item in on["results"]] == ["a", "c"]
    assert on["embedding_control"] == ["a", "b"]
    extra = on["results"][1]
    assert extra["cosine"] == 0
    assert extra["embedding_rank"] == 3
    assert extra["below_direct_similarity"]
    assert extra["outside_expanded_embedding"]
    assert extra["association_score"] == pytest.approx(0.08)
    assert extra["score"] == pytest.approx(extra["base_score"] + 0.08)
    assert extra["paths"] == [
        {
            "source": "a",
            "target": "c",
            "weight": 0.8,
            "boost": pytest.approx(0.08),
            "reason": "co_retrieval",
            "reinforcements": 3,
        }
    ]
    assert off["revision"] == on["revision"] == 7
    assert off["budget_chars"] == on["budget_chars"]
    assert graph["edges"][0]["weight"] == 0.8
    # No edge means no invented implicit association, even with spare capacity.
    graph["edges"] = []
    assert len(retrieve(graph, "question", [1, 0, 0], top_k=1)["results"]) == 1


def gateway(create):
    provider = SimpleNamespace(
        meta=lambda: SimpleNamespace(id="test/chat"),
        client=SimpleNamespace(embeddings=SimpleNamespace(create=create)),
    )
    return SimpleNamespace(
        get_all_embedding_providers=lambda: [],
        get_using_provider=lambda: provider,
        get_provider_by_id=lambda provider_id: (
            provider if provider_id == "test/chat" else None
        ),
    )


@pytest.mark.asyncio
async def test_semantic_reindex_preserves_memory_and_comparison_embeds_query_once(
    tmp_path,
):
    memory = HeLaMemoryService(tmp_path / "memory.db")
    a = await memory.remember(
        "alice", "one", event_key="turn1", origin={"conversation_id": "chat"}
    )
    b = await memory.remember(
        "alice", "two", event_key="turn2", origin={"conversation_id": "chat"}
    )
    original = memory._read("alice")
    create = AsyncMock(
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0, 3]),
                SimpleNamespace(index=0, embedding=[4, 0]),
            ]
        )
    )
    memory.context = gateway(create)
    encoder = "chat-embedding:test/chat"
    result = await memory.reindex("alice", encoder)
    assert result == {"encoder": encoder, "count": 2}
    indexed = memory._read("alice")
    assert indexed["encoder"] == encoder
    assert indexed["nodes"][a]["embedding"] == [1, 0]
    assert indexed["nodes"][b]["embedding"] == [0, 1]
    assert indexed["edges"] == original["edges"]
    for nid in (a, b):
        assert {k: v for k, v in indexed["nodes"][nid].items() if k != "embedding"} == {
            k: v for k, v in original["nodes"][nid].items() if k != "embedding"
        }
    assert create.call_args.kwargs == {
        "model": "text-embedding-3-small",
        "input": ["one", "two"],
    }
    create.return_value = SimpleNamespace(
        data=[SimpleNamespace(index=0, embedding=[1, 0])]
    )
    create.reset_mock()
    comparison = await memory.compare("alice", "question", top_k=1)
    assert create.await_count == 1
    assert comparison["base"]["encoder"] == comparison["helamem"]["encoder"] == encoder
    assert memory._read("alice") == indexed
    await memory.remember("alice", "new conversation", event_key="turn3")
    assert len(memory._read("alice")["nodes"]) == 3
    assert all(
        len(n["embedding"]) == 2 for n in memory._read("alice")["nodes"].values()
    )


@pytest.mark.asyncio
async def test_reindex_failure_and_concurrent_chat_do_not_mix_vectors(tmp_path):
    memory = HeLaMemoryService(tmp_path / "memory.db")
    await memory.remember("alice", "one")
    before = memory._read("alice")
    create = AsyncMock(
        return_value=SimpleNamespace(data=[SimpleNamespace(index=4, embedding=[1, 0])])
    )
    memory.context = gateway(create)
    with pytest.raises(ValueError, match="missing or duplicate"):
        await memory.reindex("alice", "chat-embedding:test/chat")
    assert memory._read("alice") == before

    async def concurrent(**kwargs):
        await memory.remember("alice", "arrived while indexing")
        return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[1, 0])])

    create.side_effect = concurrent
    with pytest.raises(ValueError, match="新聊天写入"):
        await memory.reindex("alice", "chat-embedding:test/chat")
    graph = memory._read("alice")
    assert len(graph["nodes"]) == 2
    assert graph["encoder"] == before["encoder"]
    assert all(len(n["embedding"]) == 512 for n in graph["nodes"].values())
