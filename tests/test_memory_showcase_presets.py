from copy import deepcopy
from unittest.mock import AsyncMock, Mock

import pytest

from persbot.core.memory.comparison import compare_fixed
from persbot.core.memory.presets import PARENTHOOD_QUERY, prepare_preset
from persbot.core.memory.service import HeLaMemoryService


def preset_graph():
    nodes = {
        "parent": {
            "id": "parent",
            "origin": {"title": "单亲家庭的挑战"},
            "kind": "episodic",
            "content": "parent evidence",
            "embedding": [1, 0],
        },
        "home": {
            "id": "home",
            "origin": {"title": "温暖的家"},
            "kind": "episodic",
            "content": "home evidence",
            "embedding": [0.6, 0.8],
        },
        "summary": {
            "id": "summary",
            "origin": {"title": "会话 2 · 归纳 1"},
            "kind": "semantic",
            "content": "summary evidence",
            "embedding": [0.8, 0.6],
        },
    }
    return {
        "nodes": nodes,
        "edges": [
            {"source": "parent", "target": "home", "weight": 0.4, "reason": "temporal"},
            {"source": "home", "target": "summary", "weight": 0.5, "reason": "consolidation"},
        ],
        "encoder": "test-semantic",
        "revision": 9,
    }


def test_preset_only_adjusts_a_copy_of_two_existing_edges_and_labels_paths():
    graph = preset_graph()
    original = deepcopy(graph)
    demonstration, presentation = prepare_preset(graph, "parenthood", PARENTHOOD_QUERY, 4)
    assert graph == original
    assert demonstration["nodes"] == original["nodes"]
    assert demonstration["revision"] == original["revision"]
    assert all(e["weight"] == 1.0 for e in demonstration["edges"])
    assert presentation["mode"] == "preset"
    assert [e["stored_weight"] for e in presentation["overrides"]] == [0.4, 0.5]
    live_pair = compare_fixed(graph, PARENTHOOD_QUERY, [1, 0])
    demo_pair = compare_fixed(demonstration, PARENTHOOD_QUERY, [1, 0])
    # The baseline selection/scores stay fixed; its metadata can report a new
    # activated rank on the other side of the comparison.
    baseline_fields = ("id", "embedding_rank", "selected_rank", "cosine", "score", "content", "paths")
    assert [
        {key: item[key] for key in baseline_fields}
        for item in live_pair["base"]["results"]
    ] == [
        {key: item[key] for key in baseline_fields}
        for item in demo_pair["base"]["results"]
    ]
    for item in demo_pair["helamem"]["results"]:
        for path in item["paths"]:
            assert path["preset_weight"] is True
            assert path["stored_weight"] in [0.4, 0.5]
    assert graph == original


@pytest.mark.parametrize("preset,query,k", [("unknown", PARENTHOOD_QUERY, 4), ("parenthood", "another question", 4), ("parenthood", PARENTHOOD_QUERY, 2)])
def test_preset_rejects_unrelated_questions_or_counts(preset, query, k):
    with pytest.raises(ValueError):
        prepare_preset(preset_graph(), preset, query, k)


def test_preset_does_not_invent_missing_memories_or_edges():
    graph = preset_graph()
    graph["edges"].pop()
    with pytest.raises(ValueError, match="原始关联不存在"):
        prepare_preset(graph, "parenthood", PARENTHOOD_QUERY, 4)
    graph["nodes"].pop("home")
    with pytest.raises(ValueError, match="唯一记忆"):
        prepare_preset(graph, "parenthood", PARENTHOOD_QUERY, 4)


@pytest.mark.asyncio
async def test_preset_service_does_not_write_or_change_following_live_query(tmp_path):
    service = HeLaMemoryService(tmp_path / "memory.db")
    graph = preset_graph()
    original = deepcopy(graph)
    service._read = Mock(return_value=graph)
    service._update = Mock(side_effect=AssertionError("Showcase must never write"))
    service._embed = AsyncMock(return_value=[1, 0])
    demo = await service.compare_fixed("alice", PARENTHOOD_QUERY, preset="parenthood")
    live = await service.compare_fixed("alice", PARENTHOOD_QUERY)
    assert demo["presentation"]["mode"] == "preset"
    assert "presentation" not in live
    assert graph == original
    assert service._embed.await_count == 2
    service._update.assert_not_called()
