"""HeLa-Mem graph mechanics adapted for Persbot.

Source: ReinerBRO/HeLa-Mem, hela_mem/hebbian_memory.py (68f19b3).
Preserves weighted associations, co-retrieval reinforcement and spreading
activation. Retrieval is read-only; learning is committed after a completed
turn. The paper's base + associative paths share a bounded context budget.
"""

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone

KINDS = {"episodic", "semantic", "profile", "pattern"}
LOCAL_ENCODER = "local-lexical-v1"


def terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{2,}", text.lower())
    for part in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(part[i : i + 2] for i in range(len(part) - 1))
    return set(words)


def normalize(vector: list[float]) -> list[float]:
    if not vector or not all(math.isfinite(v) for v in vector):
        raise ValueError("Embedding must be a non-empty finite vector")
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def lexical_embedding(text: str) -> list[float]:
    """Offline fallback; explicitly not a pretrained semantic embedding."""
    counts = Counter(terms(text))
    vector = [0.0] * 512
    for term, count in counts.items():
        index = int.from_bytes(hashlib.blake2b(term.encode(), digest_size=4).digest())
        vector[index % len(vector)] += count
    return normalize(vector)


def associate(graph: dict, source: str, target: str, weight: float, reason: str):
    if source == target:
        return
    source, target = sorted((source, target))
    edge = next(
        (e for e in graph["edges"] if e["source"] == source and e["target"] == target),
        None,
    )
    if edge:
        edge["weight"] = min(1.0, edge["weight"] + weight)
        if reason == "co_retrieval":
            edge["reinforcements"] = edge.get("reinforcements", 0) + 1
    else:
        graph["edges"].append(
            {
                "source": source,
                "target": target,
                "weight": weight,
                "reason": reason,
                "reinforcements": 0,
            }
        )


def reinforce(graph: dict, ids: list[str]) -> list[dict]:
    changes = []
    ids = list(dict.fromkeys(i for i in ids if i in graph["nodes"]))
    for index, source in enumerate(ids):
        for target in ids[index + 1 :]:
            pair = sorted((source, target))
            old = next(
                (
                    e["weight"]
                    for e in graph["edges"]
                    if [e["source"], e["target"]] == pair
                ),
                0.0,
            )
            associate(graph, source, target, 0.01, "co_retrieval")
            changes.append(
                {
                    "source": source,
                    "target": target,
                    "before": old,
                    "after": min(1.0, old + 0.01),
                }
            )
    return changes


def retrieve(
    graph: dict,
    query: str,
    embedding: list[float],
    *,
    associative: bool = True,
    top_k: int = 3,
    budget: int = 6000,
    now: float | None = None,
) -> dict:
    """Return evidence and numeric paths without mutating the memory graph."""
    query_vector = normalize(embedding)
    query_terms = terms(query)
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    candidates = {}
    for nid, node in graph["nodes"].items():
        vector = node["embedding"]
        if len(vector) != len(query_vector):
            raise ValueError("Memory embedding dimensions do not match the encoder")
        cosine = sum(a * b for a, b in zip(query_vector, vector, strict=True))
        overlap = len(query_terms & set(node["keywords"])) / max(len(query_terms), 1)
        age = max(0, now - node["created_at"]) / 86400
        decay = math.exp(-age / 60) if node["kind"] == "episodic" else 1.0
        base = ((cosine + 1) / 2 + 0.5 * overlap) * decay
        candidates[nid] = {
            "id": nid,
            "node": node,
            "cosine": cosine,
            "base_score": base,
            "score": base,
            "association_score": 0.0,
            "paths": [],
            "relevant": cosine > 0.05 or overlap > 0,
        }
    for field, score in (("embedding_rank", "cosine"), ("base_rank", "base_score")):
        for rank, item in enumerate(
            sorted(candidates.values(), key=lambda c: (-c[score], c["id"])), start=1
        ):
            item[field] = rank
    direct = sorted(
        (c for c in candidates.values() if c["relevant"]),
        key=lambda c: (-c["base_score"], c["id"]),
    )[:top_k]
    direct_ids = {c["id"] for c in direct}
    if associative:
        for edge in graph["edges"]:
            for source, target in (
                (edge["source"], edge["target"]),
                (edge["target"], edge["source"]),
            ):
                if source not in candidates or target not in candidates:
                    continue
                start = candidates[source]
                if source not in direct_ids or start["base_score"] <= 0.4:
                    continue
                boost = 0.1 * start["base_score"] * edge["weight"]
                finish = candidates[target]
                finish["association_score"] += boost
                finish["score"] += boost
                finish["paths"].append(
                    {
                        "source": source,
                        "target": target,
                        "weight": edge["weight"],
                        "boost": boost,
                        "reason": edge.get("reason", "unknown"),
                        "reinforcements": edge.get("reinforcements", 0),
                    }
                )
    for rank, item in enumerate(
        sorted(candidates.values(), key=lambda c: (-c["score"], c["id"])), start=1
    ):
        item["activated_rank"] = rank
    extra = sorted(
        (
            c
            for c in candidates.values()
            if c["id"] not in direct_ids and c["association_score"] > 0
        ),
        key=lambda c: (-c["score"], c["id"]),
    )[:2]
    results, blocks = [], []
    for item in direct + extra:
        node = item["node"]
        block = {"memory_id": item["id"], "kind": node["kind"], "text": node["content"]}
        if len(json.dumps(blocks + [block], ensure_ascii=False)) > budget:
            continue
        blocks.append(block)
        results.append(
            {k: v for k, v in item.items() if k not in {"relevant", "node"}}
            | {
                "content": node["content"],
                "kind": node["kind"],
                "source_ids": node.get("source_ids", []),
                "origin": node.get("origin", {}),
                "source": "base" if item["id"] in direct_ids else "hebbian",
            }
        )
    context = json.dumps(blocks, ensure_ascii=False) if blocks else ""
    direct_cosines = [item["cosine"] for item in results if item["source"] == "base"]
    expanded_count = len(results)
    for item in results:
        item["below_direct_similarity"] = bool(direct_cosines) and item["cosine"] < min(
            direct_cosines
        )
        item["outside_expanded_embedding"] = item["embedding_rank"] > expanded_count
    return {
        "query": query,
        "mode": "helamem" if associative else "base",
        "results": results,
        "context": context,
        "context_chars": len(context),
        "budget_chars": budget,
        "total_nodes": len(graph["nodes"]),
        "revision": graph["revision"],
        "top_k": top_k,
        "max_associative": 2 if associative else 0,
        "embedding_control": [
            item["id"]
            for item in sorted(
                candidates.values(), key=lambda c: (-c["cosine"], c["id"])
            )[:expanded_count]
        ],
        "strategy": "vector_keyword_recency",
    }
