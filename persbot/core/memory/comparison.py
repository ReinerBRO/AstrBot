"""Read-only, equal-cardinality ablation of vector retrieval and activation.

This showcase intentionally isolates graph activation from the keyword/recency
terms and extra-result slots used by the normal chat retrieval policy.
"""

from .hebbian import normalize

ACTIVATION_SCALE = 0.1
ACTIVATION_THRESHOLD = 0.4


def compare_fixed(graph: dict, query: str, embedding: list[float], top_k=4) -> dict:
    """Rank the same candidates twice, selecting exactly min(K, N) each time.

    Results retain full evidence regardless of text length. This compares memory
    selection, not answer generation or equal-token context packing.
    """
    if type(top_k) is not int or not 1 <= top_k <= 10:
        raise ValueError("Final Top-K must be an integer between 1 and 10")
    query_vector = normalize(embedding)
    candidates = {}
    for nid, node in graph["nodes"].items():
        vector = normalize(node["embedding"])
        if len(vector) != len(query_vector):
            raise ValueError("Memory embedding dimensions do not match the encoder")
        cosine = sum(a * b for a, b in zip(query_vector, vector, strict=True))
        cosine = min(1.0, max(-1.0, cosine))
        # A monotonic mapping preserves pure cosine ranking and the existing
        # activation coefficient/threshold, without keyword or recency terms.
        base = (cosine + 1) / 2
        candidates[nid] = {
            "id": nid,
            "content": node["content"],
            "kind": node["kind"],
            "origin": node.get("origin", {}),
            "source_ids": node.get("source_ids", []),
            "cosine": cosine,
            "base_score": base,
            "association_score": 0.0,
            "score": base,
            "paths": [],
        }
    vector_order = sorted(candidates.values(), key=lambda c: (-c["cosine"], c["id"]))
    for rank, item in enumerate(vector_order, start=1):
        item["embedding_rank"] = rank
    seeds = vector_order[:top_k]
    seed_ids = {item["id"] for item in seeds}
    # Propagate one hop from the unchanged vector Top-K; never recurse through
    # updated scores or reserve additional slots for associated memories.
    for edge in graph["edges"]:
        for source, target in (
            (edge["source"], edge["target"]),
            (edge["target"], edge["source"]),
        ):
            if source not in seed_ids or target not in candidates:
                continue
            start = candidates[source]
            if start["base_score"] <= ACTIVATION_THRESHOLD or edge["weight"] <= 0:
                continue
            boost = ACTIVATION_SCALE * start["base_score"] * edge["weight"]
            finish = candidates[target]
            finish["association_score"] += boost
            finish["paths"].append(
                {
                    "source": source,
                    "target": target,
                    "weight": edge["weight"],
                    "boost": boost,
                    "reason": edge.get("reason", "unknown"),
                    "reinforcements": edge.get("reinforcements", 0),
                }
                | (
                    {"preset_weight": True, "stored_weight": edge["stored_weight"]}
                    if edge.get("preset_weight")
                    else {}
                )
            )
    for item in candidates.values():
        item["score"] = item["base_score"] + item["association_score"]
    activated_order = sorted(candidates.values(), key=lambda c: (-c["score"], c["id"]))
    for rank, item in enumerate(activated_order, start=1):
        item["activated_rank"] = rank
    activated = activated_order[:top_k]
    activated_ids = {item["id"] for item in activated}
    sides = {}
    for mode, selection in (("base", seeds), ("helamem", activated)):
        results = []
        for rank, item in enumerate(selection, start=1):
            membership = (
                "shared"
                if item["id"] in seed_ids & activated_ids
                else "vector_only"
                if mode == "base"
                else "hela_only"
            )
            result = item | {
                "selected_rank": rank,
                "membership": membership,
                "source": "hebbian" if membership == "hela_only" else "base",
                "outside_vector_top_k": item["id"] not in seed_ids,
            }
            if mode == "base":
                result.update(score=item["base_score"], association_score=0.0, paths=[])
            results.append(result)
        sides[mode] = {
            "query": query,
            "mode": mode,
            "results": results,
            "top_k": top_k,
            "effective_k": len(seeds),
            "total_nodes": len(candidates),
            "revision": graph["revision"],
            "encoder": graph["encoder"],
            "strategy": "fixed_k_vector_activation",
            "content_chars": sum(len(item["content"]) for item in results),
            "activation_scale": ACTIVATION_SCALE,
            "activation_threshold": ACTIVATION_THRESHOLD,
        }
    return sides
