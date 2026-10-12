from copy import deepcopy
from math import sqrt
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from quart import Quart, g

from persbot.core.memory.comparison import compare_fixed
from persbot.core.memory.history import live_scope
from persbot.core.memory.service import HeLaMemoryService
from persbot.dashboard.routes.memory import MemoryRoute
from persbot.dashboard.routes.route import RouteContext


def graph_fixture():
    # The fifth memory can replace the fourth only through the saved edge.
    cosines = {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.6, "e": 0.5, "f": 0.1}
    return {
        "encoder": "test-semantic",
        "revision": 7,
        "nodes": {
            nid: {
                "id": nid,
                "embedding": [cosine, sqrt(1 - cosine**2)],
                "content": nid * 15000 if nid == "a" else nid,
                "kind": "episodic",
                "created_at": 0 if nid == "a" else 9999999999,
                "keywords": ["question"] if nid == "f" else [],
                "origin": {"session_id": "test-session"},
            }
            for nid, cosine in cosines.items()
        },
        "edges": [
            {
                "source": "a",
                "target": "e",
                "weight": 1,
                "reason": "co_retrieval",
                "reinforcements": 3,
            }
        ],
    }


def ids(side):
    return [item["id"] for item in side["results"]]


def test_fixed_k_is_pure_cosine_and_equal_count_without_budget_skips():
    graph = graph_fixture()
    original = deepcopy(graph)
    pair = compare_fixed(graph, "question", [1, 0])
    assert ids(pair["base"]) == ["a", "b", "c", "d"]
    assert ids(pair["helamem"]) == ["a", "b", "c", "e"]
    assert len(pair["base"]["results"]) == len(pair["helamem"]["results"]) == 4
    assert [r["embedding_rank"] for r in pair["base"]["results"]] == [1, 2, 3, 4]
    assert [r["selected_rank"] for r in pair["helamem"]["results"]] == [1, 2, 3, 4]
    assert len(pair["base"]["results"][0]["content"]) == 15000
    assert pair["base"]["results"][-1]["membership"] == "vector_only"
    swapped = pair["helamem"]["results"][-1]
    assert swapped["membership"] == "hela_only"
    assert swapped["source"] == "hebbian"
    assert swapped["outside_vector_top_k"]
    assert swapped["embedding_rank"] == 5
    assert swapped["activated_rank"] == 4
    assert swapped["base_score"] == pytest.approx(0.75)
    assert swapped["association_score"] == pytest.approx(0.095)
    assert swapped["score"] == pytest.approx(0.845)
    assert swapped["paths"] == [
        {
            "source": "a",
            "target": "e",
            "weight": 1,
            "boost": pytest.approx(0.095),
            "reason": "co_retrieval",
            "reinforcements": 3,
        }
    ]
    assert all(not item["paths"] for item in pair["base"]["results"])
    assert pair["base"]["revision"] == pair["helamem"]["revision"] == 7
    assert graph == original


@pytest.mark.parametrize("weight", [0, 0.01])
def test_no_forced_swap_or_extra_slots_with_absent_or_weak_activation(weight):
    graph = graph_fixture()
    graph["edges"][0]["weight"] = weight
    pair = compare_fixed(graph, "question", [1, 0])
    assert ids(pair["base"]) == ids(pair["helamem"]) == ["a", "b", "c", "d"]
    assert all(r["membership"] == "shared" for r in pair["helamem"]["results"])


@pytest.mark.parametrize("count", [0, 1, 3, 4, 6])
def test_small_graphs_return_equal_minimum_k_and_node_count(count):
    graph = graph_fixture()
    graph["nodes"] = dict(list(graph["nodes"].items())[:count])
    pair = compare_fixed(graph, "question", [1, 0])
    assert len(ids(pair["base"])) == len(ids(pair["helamem"])) == min(4, count)
    assert pair["base"]["effective_k"] == min(4, count)


def test_ties_are_deterministic_and_propagation_does_not_use_updated_scores():
    graph = graph_fixture()
    graph["nodes"]["d"]["embedding"] = graph["nodes"]["c"]["embedding"]
    graph["edges"].append({"source": "b", "target": "a", "weight": 1})
    forward = compare_fixed(graph, "question", [1, 0])
    graph["nodes"] = dict(reversed(list(graph["nodes"].items())))
    graph["edges"].reverse()
    backward = compare_fixed(graph, "question", [1, 0])
    assert ids(forward["base"]) == ids(backward["base"]) == ["a", "b", "c", "d"]
    assert ids(forward["helamem"]) == ids(backward["helamem"])
    for a, b in zip(forward["helamem"]["results"], backward["helamem"]["results"]):
        assert a["score"] == pytest.approx(b["score"])


@pytest.mark.asyncio
async def test_fixed_comparison_uses_one_snapshot_and_embedding_without_writes(tmp_path):
    memory = HeLaMemoryService(tmp_path / "memory.db")
    graph = graph_fixture()
    memory._read = Mock(return_value=graph)
    memory._embed = AsyncMock(return_value=[1, 0])
    original = deepcopy(graph)
    pair = await memory.compare_fixed("alice", "question")
    memory._read.assert_called_once_with("alice")
    memory._embed.assert_awaited_once_with("question", "test-semantic")
    assert pair["base"]["encoder"] == pair["helamem"]["encoder"]
    assert graph == original


@pytest.mark.parametrize("top_k", [-1, 0, 11, True, 2.5, "4", None])
@pytest.mark.asyncio
async def test_invalid_fixed_k_rejected_before_embedding(tmp_path, top_k):
    memory = HeLaMemoryService(tmp_path / "memory.db")
    memory._embed = AsyncMock()
    with pytest.raises(ValueError, match="Final Top-K"):
        await memory.compare_fixed("alice", "question", top_k=top_k)
    memory._embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_fixed_route_defaults_to_four_and_rejects_other_owners():
    app = Quart(__name__)
    service = SimpleNamespace(compare_fixed=AsyncMock(return_value={"tested": True}))

    @app.before_request
    async def identify():
        g.username = "alice"

    MemoryRoute(
        RouteContext({}, app),
        SimpleNamespace(star_context=SimpleNamespace(memory_service=service)),
    )
    client = app.test_client()
    response = await client.post("/api/memory/compare-fixed", json={"query": "question"})
    assert response.status_code == 200
    service.compare_fixed.assert_awaited_once_with(
        live_scope("webchat", "webchat", "private", "alice"), "question", top_k=4
    )
    response = await client.post(
        "/api/memory/compare-fixed", json={"query": "question", "scope": "someone-else"}
    )
    assert response.status_code == 400
    assert service.compare_fixed.await_count == 1
