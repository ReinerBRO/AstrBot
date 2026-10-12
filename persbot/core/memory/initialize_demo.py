"""Install the portable group-meeting conversations into the current user's Chat."""

import asyncio
import json
from pathlib import Path

from .hebbian import terms
from .history import live_scope
from .initialize_chat import initialize_chat
from .initialize_showcase import initialize_showcase
from .service import GATEWAY_ENCODER_PREFIX


def load_demo():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "chat_demo.json").read_text(
            encoding="utf-8"
        )
    )


async def initialize_demo(service, db, owner):
    provider = service.context.get_using_provider() if service.context else None
    if (
        not provider
        or provider.get_model() != "gpt-4o-mini"
        or not hasattr(getattr(provider, "client", None), "embeddings")
    ):
        raise ValueError(
            "请先将当前聊天模型设为 gpt-4o-mini，并配置支持 text-embedding-3-small 的网关和 Key"
        )
    if service._answer_lock.locked():
        raise ValueError("记忆任务正在运行，请完成后再初始化")
    async with service._answer_lock:
        encoder = GATEWAY_ENCODER_PREFIX + provider.meta().id
        scope = live_scope("webchat", "webchat", None, owner)
        current = await asyncio.to_thread(service._read, scope)
        if current["nodes"] and current["encoder"] != encoder:
            raise ValueError("已有记忆使用不同编码器，请先在记忆设置中重建语义索引")
        bundle = load_demo()
        source_scope = bundle["source_scope"]
        source = await asyncio.to_thread(service._read, source_scope)
        if source["nodes"] and source["encoder"] != encoder:
            raise ValueError("初始化源的编码器与当前模型不一致，请使用原提供商配置")
        if not source["nodes"]:
            nodes = list(bundle["nodes"].values())
            vectors = await service._embed_many(
                [node["content"] for node in nodes], encoder
            )
            for node, vector in zip(nodes, vectors, strict=True):
                node.update(
                    embedding=vector,
                    keywords=sorted(terms(node["content"])),
                    access_count=0,
                )
            await asyncio.to_thread(
                service._update,
                source_scope,
                lambda graph: graph.update(
                    nodes={node["id"]: node for node in nodes},
                    edges=bundle["edges"],
                    encoder=encoder,
                    replay={"status": "complete"},
                ),
            )
        chat = await initialize_chat(service, db, owner, source_scope)
        career = await initialize_showcase(service, db, owner)
        await service.configure(enabled=True, encoder=encoder)
        return {
            "scope": scope,
            "encoder": encoder,
            "memories": chat["memories"] + career["memories"],
            "turns": chat["turns"] + career["turns"],
            "sessions": chat["sessions"] + career["sessions"],
        }
