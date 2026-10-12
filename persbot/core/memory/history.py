"""Build memory only from stored, owner-scoped conversation turns."""

import hashlib
import json

from persbot.core.utils.datetime_utils import to_utc_timestamp


def live_scope(platform, platform_id, group, sender):
    parts = [platform, platform_id, group or "private", sender]
    return "live:" + hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:24]


def text_content(record):
    content = record.content
    return "\n".join(
        part["text"]
        for part in content.get("message", [])
        if part.get("type") == "plain" and isinstance(part.get("text"), str)
    ).strip()


def completed_turns(records, owner):
    """Retain message identity and original role boundaries; never generate turns."""
    pending = None
    turns = []
    for record in sorted(records, key=lambda item: item.id):
        role = record.content.get("type")
        text = text_content(record)
        if role == "user":
            pending = record if record.sender_id == owner and text else None
        elif role == "bot" and pending and text:
            turns.append((pending, record))
            pending = None
    return turns


class ConversationMemoryImporter:
    def __init__(self, service, db):
        self.service = service
        self.db = db

    async def records(self, session_id):
        records = []
        page = 1
        while True:
            batch = await self.db.get_platform_message_history(
                "webchat", session_id, page=page, page_size=500
            )
            records.extend(batch)
            if len(batch) < 500:
                return records
            page += 1
            if page > 20:
                raise ValueError("会话超过 10000 条消息，请先分段导出后接入")

    async def inventory(self, owner):
        excluded = await self.service.excluded_conversations()
        sessions, total = await self.db.get_platform_sessions_by_creator_paginated(
            creator=owner, platform_id="webchat", page=1, page_size=100
        )
        result = []
        excluded_count = 0
        for item in sessions:
            session = item["session"]
            if session.session_id in excluded:
                excluded_count += 1
                continue
            if session.is_group:
                continue
            turns = completed_turns(await self.records(session.session_id), owner)
            if turns:
                result.append(
                    {
                        "session_id": session.session_id,
                        "title": session.display_name or "未命名对话",
                        "turn_count": len(turns),
                    }
                )
        return {
            "sessions": result,
            "excluded_count": excluded_count,
            "has_more": total > 100,
        }

    async def ingest(self, owner, session_id):
        session = await self.db.get_platform_session_by_id(session_id)
        if not session or session.creator != owner:
            raise ValueError("只能接入当前用户自己的会话")
        if session.platform_id != "webchat" or session.is_group:
            raise ValueError("当前入口仅接入 WebChat 私聊，避免混合不同用户的记忆")
        if session_id in await self.service.excluded_conversations():
            raise ValueError("该会话是已隔离的联调测试记录，不能作为用户记忆接入")
        turns = completed_turns(await self.records(session_id), owner)
        if not turns:
            raise ValueError("会话中没有已完成的文本问答")
        scope = live_scope("webchat", "webchat", None, owner)
        conversation = f"webchat!{owner}!{session_id}"
        graph = await self.service.snapshot(scope)
        existing = [
            node
            for node in graph["nodes"]
            if node["origin"].get("conversation_id") == conversation
        ]
        consumed = set()
        imported = 0
        skipped = 0
        for index, (user, assistant) in enumerate(turns, start=1):
            content = (
                f"User: {text_content(user)}\nAssistant: {text_content(assistant)}"
            )
            event_key = f"history:webchat:{user.id}:{assistant.id}"
            match = next(
                (
                    node
                    for node in existing
                    if node["id"] not in consumed
                    and (
                        node.get("event_key") == event_key or node["content"] == content
                    )
                ),
                None,
            )
            if match:
                consumed.add(match["id"])
                continue
            if len(content) > 12000:
                skipped += 1
                continue
            await self.service.remember(
                scope,
                content,
                label=f"webchat · {owner}",
                event_key=event_key,
                created_at=to_utc_timestamp(user.created_at),
                origin={
                    "method": "conversation_history",
                    "user_text": text_content(user),
                    "assistant_text": text_content(assistant),
                    "platform": "webchat",
                    "conversation_id": conversation,
                    "session_id": session_id,
                    "conversation_title": session.display_name or "未命名对话",
                    "turn_index": index,
                    "sender_id": owner,
                    "message_ids": [str(user.id), str(assistant.id)],
                    "topic": session.display_name or f"对话 {session_id[:8]}",
                },
            )
            imported += 1
        return {
            "scope": scope,
            "imported": imported,
            "turns": len(turns),
            "skipped": skipped,
        }
