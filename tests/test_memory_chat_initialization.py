import json
from types import SimpleNamespace

import pytest
from sqlmodel import select

from persbot.core.db.po import ConversationV2, Preference
from persbot.core.db.sqlite import SQLiteDatabase
from persbot.core.memory.history import ConversationMemoryImporter, live_scope
from persbot.core.memory.initialize_chat import initialize_chat
from persbot.core.memory.service import HeLaMemoryService, MemoryConversationHooks


async def make_source(memory):
    scope = "locomo:fixture:Alice"
    for session in range(1, 4):
        ids = []
        for turn in range(1, 3):
            user = f"第 {session} 次聊天，我喜欢绿茶 {turn}"
            answer = "记住了你的喜好。"
            ids.append(
                await memory.remember(
                    scope,
                    f"User: {user}\nAssistant: {answer}",
                    origin={
                        "method": "locomo_replay",
                        "session_number": session,
                        "turn_index": turn,
                        "source_text": user,
                        "model_reply": answer,
                        "conversation_id": f"fixture:{session}",
                        "title": "茶与生活",
                    },
                )
            )
        await memory.consolidate(scope, ids)
    memory._update(scope, lambda graph: graph.update(replay={"status": "complete"}))
    return scope


@pytest.mark.asyncio
async def test_initialization_and_new_chat_share_memory_without_duplication(tmp_path):
    db = SQLiteDatabase(str(tmp_path / "chat.db"))
    memory = HeLaMemoryService(tmp_path / "memory.db")
    try:
        source = await make_source(memory)
        before = await memory.snapshot(source)
        scope = live_scope("webchat", "webchat", None, "alice")
        original = await memory.remember(scope, "保留我已有的真实记忆")
        result = await initialize_chat(memory, db, "alice", source)
        assert result["scope"] == scope
        assert result["turns"] == 6
        assert result["memories"] == 9
        assert len(result["sessions"]) == 3
        graph = await memory.snapshot(scope)
        assert len(graph["nodes"]) == 10
        assert original in {node["id"] for node in graph["nodes"]}
        assert graph["edges"] == before["edges"]
        importer = ConversationMemoryImporter(memory, db)
        for session in result["sessions"]:
            records = await importer.records(session["id"])
            assert len(records) == 4
            assert records[0].content["type"] == "bot"
            assert (await importer.ingest("alice", session["id"]))["imported"] == 0
            with pytest.raises(ValueError):
                await importer.ingest("bob", session["id"])
        async with db.get_db() as transaction:
            conversations = (
                (await transaction.execute(select(ConversationV2))).scalars().all()
            )
            preferences = (
                (await transaction.execute(select(Preference))).scalars().all()
            )
            assert len(conversations) == len(preferences) == 3
            assert all(len(c.content) == 4 for c in conversations)
            assert all(
                c.user_id.startswith("webchat:FriendMessage:webchat!alice!")
                for c in conversations
            )
            assert {p.value["val"] for p in preferences} == {
                c.conversation_id for c in conversations
            }

        # The next ordinary Chat turn recalls and extends the initialized graph.
        sid = result["sessions"][0]["id"]
        extras = {}
        event = SimpleNamespace(
            session_id=f"webchat!alice!{sid}",
            message_str="我喜欢什么茶？",
            message_obj=SimpleNamespace(message_id="new-live-turn"),
            get_sender_id=lambda: "alice",
            get_sender_name=lambda: "alice",
            get_platform_name=lambda: "webchat",
            get_platform_id=lambda: "webchat",
            get_group_id=lambda: "",
            get_extra=extras.get,
            set_extra=lambda k, v: extras.__setitem__(k, v),
        )
        memory.context = SimpleNamespace(
            get_db=lambda: db, get_all_embedding_providers=lambda: []
        )
        hook = MemoryConversationHooks(memory)
        request = SimpleNamespace(prompt=event.message_str, system_prompt="Assistant")
        await hook.before(event, request)
        assert "绿茶" in request.system_prompt
        await hook.after(
            event,
            SimpleNamespace(
                is_chunk=False,
                role="assistant",
                tools_call_name=[],
                completion_text="你喜欢绿茶。",
            ),
        )
        assert extras["hela_memory_pending"]["scope"] == result["scope"]
        after = await memory.snapshot(scope)
        assert len(after["nodes"]) == 11
        node = after["nodes"][-1]
        assert node["origin"]["session_id"] == sid
        assert node["origin"]["user_text"] == event.message_str
        assert node["origin"]["conversation_title"] == result["sessions"][0]["title"]
        assert await initialize_chat(memory, db, "alice", source) == result
        assert await memory.snapshot(scope) == after
        assert await memory.snapshot(source) == before
        assert not (
            await memory.snapshot(live_scope("webchat", "webchat", None, "bob"))
        )["nodes"]
    finally:
        await db.engine.dispose()


@pytest.mark.asyncio
async def test_initialization_recovers_after_chat_commit(tmp_path, monkeypatch):
    db = SQLiteDatabase(str(tmp_path / "chat.db"))
    memory = HeLaMemoryService(tmp_path / "memory.db")
    try:
        source = await make_source(memory)
        update = memory._update

        def interrupted(*args):
            raise RuntimeError("Interrupted after Chat transaction")

        monkeypatch.setattr(memory, "_update", interrupted)
        with pytest.raises(RuntimeError):
            await initialize_chat(memory, db, "alice", source)
        monkeypatch.setattr(memory, "_update", update)
        result = await initialize_chat(memory, db, "alice", source)
        importer = ConversationMemoryImporter(memory, db)
        assert len((await importer.inventory("alice"))["sessions"]) == 3
        assert (
            sum([len(await importer.records(s["id"])) for s in result["sessions"]])
            == 12
        )
        assert len((await memory.snapshot(result["scope"]))["nodes"]) == 9
        assert "locomo_replay" in json.dumps(memory._read(result["scope"]))
    finally:
        await db.engine.dispose()
