"""Install the approved showcase as persistent, owner-scoped Chat history."""

import asyncio
import time

from .answer_showcase import CASE_ID, QUESTION, career_case
from .hebbian import terms
from .history import live_scope
from .initialize_chat import initialize_chat


async def initialize_showcase(service, db, owner):
    scope = live_scope("webchat", "webchat", None, owner)
    current = await asyncio.to_thread(service._read, scope)
    if current.get("baseline", {}).get("id") == CASE_ID:
        return current["baseline"]
    case = career_case()["presentation"]["graph"]
    source_scope = f"bootstrap:{scope}:{CASE_ID}"
    source = await asyncio.to_thread(service._read, source_scope)
    if not source["nodes"]:
        encoder = (
            current["encoder"]
            if current["nodes"]
            else (await service.settings())["encoder"]
        )
        vectors = await service._embed_many(
            [n["content"] for n in case["nodes"]], encoder
        )
        nodes = {}
        for index, (node, vector) in enumerate(
            zip(case["nodes"], vectors, strict=True)
        ):
            nodes[node["id"]] = node | {
                "embedding": vector,
                "keywords": sorted(terms(node["content"])),
                "created_at": time.time() - 600 + index,
                "origin": node["origin"]
                | {
                    "baseline_case": CASE_ID,
                    "session_number": 1 if node["id"] == "M15" else 2,
                    "turn_index": index + 1,
                    "source_text": node["content"],
                    "model_reply": "记住了。",
                },
            }
        await asyncio.to_thread(
            service._update,
            source_scope,
            lambda graph: graph.update(
                nodes=nodes,
                edges=case["edges"],
                encoder=encoder,
                replay={"status": "complete"},
            ),
        )
    result = await initialize_chat(service, db, owner, source_scope)

    def install(graph):
        graph["baseline"] = result | {
            "id": CASE_ID,
            "query": QUESTION,
        }
        return graph["baseline"]

    return await asyncio.to_thread(service._update, scope, install)
