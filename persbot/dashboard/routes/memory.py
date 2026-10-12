"""Dashboard endpoints for the shared HeLa-Mem service."""

from functools import wraps

from quart import g, request

from persbot.core import logger
from persbot.core.memory.history import ConversationMemoryImporter, live_scope
from persbot.core.memory.initialize_demo import initialize_demo
from persbot.core.memory.initialize_showcase import initialize_showcase

from .route import Response, Route, RouteContext


def memory_endpoint(func):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            return Response().ok(data=await func(*args, **kwargs)).__dict__
        except (ValueError, TypeError, KeyError) as exc:
            return Response().error(str(exc)).__dict__, 400
        except Exception:
            logger.exception("Memory request failed")
            return Response().error(
                "记忆操作失败，请检查模型配置或后端日志。"
            ).__dict__, 500

    return wrapped


class MemoryRoute(Route):
    def __init__(self, context: RouteContext, core_lifecycle):
        super().__init__(context)
        self.core = core_lifecycle
        self.routes = {
            "/memory/scopes": ("GET", self.scopes),
            "/memory/graph": ("GET", self.graph),
            "/memory/settings": [("GET", self.settings), ("POST", self.configure)],
            "/memory/add": ("POST", self.add),
            "/memory/compare": ("POST", self.compare),
            "/memory/compare-fixed": ("POST", self.compare_fixed),
            "/memory/recall": ("POST", self.recall),
            "/memory/reindex": ("POST", self.reindex),
            "/memory/answer-compare": ("POST", self.answer_compare),
            "/memory/answer-fixed": ("POST", self.answer_fixed),
            "/memory/answer-showcase": ("POST", self.answer_showcase),
            "/memory/answer-cases": ("GET", self.answer_cases),
            "/memory/answer-validation": ("POST", self.answer_validation),
            "/memory/initialize-showcase": ("POST", self.initialize_showcase),
            "/memory/initialize-demo": ("POST", self.initialize_demo),
            "/memory/consolidate": ("POST", self.consolidate),
            "/memory/conversations": ("GET", self.conversations),
            "/memory/import-conversation": ("POST", self.import_conversation),
        }
        self.register_routes()

    @property
    def service(self):
        return self.core.star_context.memory_service

    @staticmethod
    def scope(data):
        current = live_scope("webchat", "webchat", None, g.get("username", "guest"))
        if data.get("scope", current) != current:
            raise ValueError("只能访问当前用户自己的聊天记忆")
        return current

    @staticmethod
    async def body():
        data = await request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")
        return data

    @memory_endpoint
    async def scopes(self):
        graph = await self.service.snapshot(self.scope({}))
        return [
            {"scope": graph["scope"], "label": "我的记忆", "count": len(graph["nodes"])}
        ]

    @property
    def importer(self):
        return ConversationMemoryImporter(self.service, self.core.star_context.get_db())

    @memory_endpoint
    async def conversations(self):
        return await self.importer.inventory(g.get("username", "guest"))

    @memory_endpoint
    async def import_conversation(self):
        data = await self.body()
        session_id = data.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("请选择要接入的会话")
        return await self.importer.ingest(g.get("username", "guest"), session_id)

    @memory_endpoint
    async def graph(self):
        graph = await self.service.snapshot(self.scope(request.args))
        graph.pop("initializations", None)
        for node in graph["nodes"]:
            node["origin"].pop("initialization_source", None)
        return graph

    @memory_endpoint
    async def recall(self):
        data = await self.body()
        return await self.service.recall(
            self.scope(data),
            data.get("query"),
            top_k=data.get("top_k", 3),
            budget=data.get("budget", 6000),
        )

    @memory_endpoint
    async def settings(self):
        return await self.service.settings()

    @memory_endpoint
    async def configure(self):
        data = await self.body()
        return await self.service.configure(
            enabled=data["enabled"], encoder=data["encoder"]
        )

    @memory_endpoint
    async def reindex(self):
        data = await self.body()
        return await self.service.reindex(self.scope(data), data.get("encoder"))

    @memory_endpoint
    async def add(self):
        data = await self.body()
        scope = self.scope(data)
        nid = await self.service.remember(
            scope,
            data.get("content"),
            kind=data.get("kind", "episodic"),
            origin={"method": "manual", "conversation_id": f"manual:{scope}"},
        )
        return {"id": nid}

    @memory_endpoint
    async def compare(self):
        data = await self.body()
        return await self.service.compare(
            self.scope(data),
            data.get("query"),
            top_k=data.get("top_k", 3),
            budget=data.get("budget", 6000),
        )

    @memory_endpoint
    async def compare_fixed(self):
        data = await self.body()
        options = {"preset": data["preset"]} if "preset" in data else {}
        return await self.service.compare_fixed(
            self.scope(data), data.get("query"), top_k=data.get("top_k", 4), **options
        )

    @memory_endpoint
    async def answer_compare(self):
        data = await self.body()
        return await self.service.answer_compare(
            self.scope(data),
            data.get("query"),
            top_k=data.get("top_k", 1),
            budget=data.get("budget", 6000),
        )

    @memory_endpoint
    async def initialize_demo(self):
        self.scope(await self.body())
        return await initialize_demo(
            self.service, self.core.star_context.get_db(), g.get("username", "guest")
        )

    @memory_endpoint
    async def initialize_showcase(self):
        self.scope(await self.body())
        return await initialize_showcase(
            self.service, self.core.star_context.get_db(), g.get("username", "guest")
        )

    @memory_endpoint
    async def answer_showcase(self):
        data = await self.body()
        return await self.service.answer_showcase(
            self.scope(data),
            preset=data.get("preset", "paper-career"),
            generation=data.get("generation", "scripted"),
        )

    @memory_endpoint
    async def answer_fixed(self):
        data = await self.body()
        return await self.service.answer_fixed(
            self.scope(data), data.get("query"), top_k=data.get("top_k", 4)
        )

    @memory_endpoint
    async def answer_cases(self):
        return await self.service.answer_cases(self.scope(request.args))

    @memory_endpoint
    async def answer_validation(self):
        data = await self.body()
        return await self.service.answer_validation(
            self.scope(data),
            data.get("case_id"),
            generation=data.get("generation", "saved"),
        )

    @memory_endpoint
    async def consolidate(self):
        data = await self.body()
        return await self.service.consolidate(self.scope(data), data.get("source_ids"))
