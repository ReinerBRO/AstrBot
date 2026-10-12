"""Explicitly hand-authored showcase settings over existing chat memories."""

PARENTHOOD_QUERY = "Why do I feel ready to become a parent?"


def prepare_preset(graph: dict, preset: str | None, query: str, top_k: int):
    if preset is None:
        return graph, None
    if preset != "parenthood":
        raise ValueError("未知的记忆演示预设")
    if query.strip() != PARENTHOOD_QUERY or top_k != 4:
        raise ValueError("该预设使用固定的家长问题和 Top-4，请点击预设演示入口")

    def find(title):
        matches = [
            node
            for node in graph["nodes"].values()
            if node.get("origin", {}).get("title") == title
        ]
        if len(matches) != 1:
            raise ValueError(f"当前记忆库缺少预设所需的唯一记忆：{title}")
        return matches[0]["id"]

    target = find("温暖的家")
    sources = [find("单亲家庭的挑战"), find("会话 2 · 归纳 1")]
    pairs = {frozenset((source, target)) for source in sources}
    edges, overrides = [], []
    for edge in graph["edges"]:
        if frozenset((edge["source"], edge["target"])) in pairs:
            overrides.append(
                {
                    "source": edge["source"],
                    "target": edge["target"],
                    "stored_weight": edge["weight"],
                    "weight": 1.0,
                }
            )
            edges.append(
                edge
                | {
                    "weight": 1.0,
                    "preset_weight": True,
                    "stored_weight": edge["weight"],
                }
            )
        else:
            edges.append(edge)
    if len(overrides) != len(pairs):
        raise ValueError("预设需要的原始关联不存在，不会自动编造记忆连线")
    return graph | {"edges": edges}, {
        "mode": "preset",
        "id": preset,
        "label": "成为家长的底气",
        "target_id": target,
        "overrides": overrides,
    }
