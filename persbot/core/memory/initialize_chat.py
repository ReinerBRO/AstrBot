"""One-shot, resumable initialization of ordinary Chat history and memory.

This is an operator utility, not a dashboard feature. It reuses completed model
responses without calling a model or loading benchmark answers.
"""

import argparse
import asyncio
import copy
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import select

from persbot.core.db.po import (
    ConversationV2,
    PlatformMessageHistory,
    PlatformSession,
    Preference,
)
from persbot.core.memory.history import live_scope
from persbot.core.memory.service import HeLaMemoryService


async def initialize_chat(service, db, owner, source_scope):
    source = await asyncio.to_thread(service._read, source_scope)
    if source.get("replay", {}).get("status") != "complete":
        raise ValueError("Initialization requires completed conversation generation")
    target_scope = live_scope("webchat", "webchat", None, owner)
    marker = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{owner}:{source_scope}"))
    target = await asyncio.to_thread(service._read, target_scope)
    if marker in target.get("initializations", {}):
        return target["initializations"][marker]
    if target["nodes"] and target["encoder"] != source["encoder"]:
        raise ValueError("Cannot merge memories with different encoders")

    episodes = sorted(
        (n for n in source["nodes"].values() if n["kind"] == "episodic"),
        key=lambda n: (n["origin"]["session_number"], n["origin"]["turn_index"]),
    )
    if not episodes:
        raise ValueError("No completed conversation turns to initialize")
    sessions = {}
    message_ids = {}
    # All three Chat stores commit together. Stable IDs allow a safe retry if
    # the process stops before the independent memory-store transaction.
    async with db.get_db() as transaction:
        async with transaction.begin():
            for number in sorted({n["origin"]["session_number"] for n in episodes}):
                turns = [n for n in episodes if n["origin"]["session_number"] == number]
                sid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{marker}:session:{number}"))
                cid = str(
                    uuid.uuid5(uuid.NAMESPACE_URL, f"{marker}:conversation:{number}")
                )
                title = f"{turns[0]['origin'].get('title') or '聊聊近况'} · {number}"
                sessions[number] = {"id": sid, "title": title}
                existing = (
                    await transaction.execute(
                        select(PlatformSession).where(PlatformSession.session_id == sid)
                    )
                ).scalar_one_or_none()
                if existing:
                    if existing.creator != owner or existing.platform_id != "webchat":
                        raise ValueError("Initialization session ownership mismatch")
                    records = (
                        (
                            await transaction.execute(
                                select(PlatformMessageHistory)
                                .where(
                                    PlatformMessageHistory.platform_id == "webchat",
                                    PlatformMessageHistory.user_id == sid,
                                )
                                .order_by(PlatformMessageHistory.id)
                            )
                        )
                        .scalars()
                        .all()
                    )
                    for record in records:
                        key = record.content.get("initialization_turn")
                        if key:
                            message_ids.setdefault(key, []).append(str(record.id))
                    continue
                created = datetime.fromtimestamp(turns[0]["created_at"], timezone.utc)
                transaction.add(
                    PlatformSession(
                        session_id=sid,
                        creator=owner,
                        platform_id="webchat",
                        display_name=title,
                        created_at=created,
                    )
                )
                history = []
                for node in turns:
                    origin = node["origin"]
                    pair = [
                        ("user", origin["source_text"]),
                        ("bot", origin["model_reply"]),
                    ]
                    for role, text in pair:
                        record = PlatformMessageHistory(
                            platform_id="webchat",
                            user_id=sid,
                            sender_id=owner if role == "user" else "bot",
                            sender_name=owner if role == "user" else "Persbot",
                            created_at=datetime.fromtimestamp(
                                node["created_at"], timezone.utc
                            )
                            + timedelta(microseconds=1 if role == "bot" else 0),
                            content={
                                "type": role,
                                "message": [{"type": "plain", "text": text}],
                                "initialization_turn": node["id"],
                            },
                        )
                        transaction.add(record)
                        await transaction.flush()
                        message_ids.setdefault(node["id"], []).append(str(record.id))
                        history.append(
                            {
                                "role": "user" if role == "user" else "assistant",
                                "content": text,
                            }
                        )
                umo = f"webchat:FriendMessage:webchat!{owner}!{sid}"
                transaction.add(
                    ConversationV2(
                        conversation_id=cid,
                        platform_id="webchat",
                        user_id=umo,
                        content=history,
                        title=title,
                        created_at=created,
                    )
                )
                transaction.add(
                    Preference(
                        scope="umo",
                        scope_id=umo,
                        key="sel_conv_id",
                        value={"val": cid},
                    )
                )

    nodes = copy.deepcopy(source["nodes"])
    for node in nodes.values():
        old = node["origin"]
        number = old.get("session_number")
        if number is None and node["source_ids"]:
            number = source["nodes"][node["source_ids"][0]]["origin"]["session_number"]
        session = sessions[number]
        if node["kind"] == "episodic" and len(message_ids.get(node["id"], [])) != 2:
            raise ValueError("Initialization history has missing or duplicate messages")
        node["origin"] = {
            "method": "conversation_history"
            if node["kind"] == "episodic"
            else old["method"],
            "platform": "webchat",
            "sender_id": owner,
            "conversation_id": f"webchat!{owner}!{session['id']}",
            "session_id": session["id"],
            "conversation_title": session["title"],
            "topic": session["title"],
            "title": old.get("title", "聊天中的发现"),
            "turn_index": old.get("turn_index"),
            "message_ids": message_ids.get(node["id"], []),
            "initialization_source": old,
        }
        if node["kind"] == "episodic":
            node["origin"].update(
                user_text=old["source_text"], assistant_text=old["model_reply"]
            )
            node["event_key"] = "history:webchat:" + ":".join(message_ids[node["id"]])
            content = f"User: {old['source_text']}\nAssistant: {old['model_reply']}"
            if node["content"] != content:
                node["embedding"] = await service._embed(content, source["encoder"])
                node["content"] = content

    result = {
        "scope": target_scope,
        "sessions": list(sessions.values()),
        "turns": len(episodes),
        "memories": len(nodes),
    }

    def merge(graph):
        if marker in graph.get("initializations", {}):
            return graph["initializations"][marker]
        if set(graph["nodes"]) & set(nodes):
            raise ValueError("Initialization memory ID collision")
        if graph["nodes"] and graph["encoder"] != source["encoder"]:
            raise ValueError("Memory encoder changed during initialization")
        graph["encoder"] = source["encoder"]
        graph["label"] = "我的记忆"
        graph["nodes"].update(nodes)
        graph["edges"].extend(copy.deepcopy(source["edges"]))
        traces = copy.deepcopy(source["traces"])
        for trace in traces:
            trace["scope"] = target_scope
        graph["traces"] = sorted(
            graph["traces"] + traces, key=lambda t: t.get("created_at", 0)
        )[-30:]
        graph.setdefault("initializations", {})[marker] = result
        return result

    return await asyncio.to_thread(service._update, target_scope, merge)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--source-scope", required=True)
    args = parser.parse_args()
    from persbot.core import db_helper
    from persbot.core.utils.persbot_path import get_persbot_data_path

    service = HeLaMemoryService(
        Path(get_persbot_data_path()) / "memory" / "helamem.sqlite3"
    )
    try:
        print(
            json.dumps(
                await initialize_chat(
                    service, db_helper, args.owner, args.source_scope
                ),
                ensure_ascii=False,
            )
        )
    finally:
        await db_helper.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
