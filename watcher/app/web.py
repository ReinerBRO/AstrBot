import json
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from app.service import WatcherService


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web_static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    service = WatcherService()

    def _parse_list_arg(name: str) -> list[str]:
        values = request.args.getlist(name)
        if not values:
            raw = request.args.get(name, "")
            values = [raw] if raw else []
        output: list[str] = []
        for item in values:
            for chunk in str(item).split(","):
                token = chunk.strip()
                if token:
                    output.append(token)
        return output

    def _parse_bool_arg(value: str | None, default: bool = False) -> bool:
        if value is None:
            return default
        text = value.strip().lower()
        if not text:
            return default
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return default

    def _sse_event(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @app.after_request
    def disable_cache(response):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory(STATIC_DIR, "favicon.svg")

    @app.get("/api/status")
    def status():
        data = service.status()
        return jsonify({"ok": True, "data": data})

    @app.get("/api/event-source/status")
    def event_source_status():
        data = service.event_source_status()
        return jsonify({"ok": True, "data": data})

    @app.get("/api/event-source/summary")
    def event_source_summary():
        data = service.event_source_summary()
        return jsonify({"ok": True, "data": data})

    @app.get("/api/monitors")
    def get_monitors():
        data = service.get_monitors()
        return jsonify(data)

    @app.get("/api/monitors/<int:monitor_index>/preview")
    def get_monitor_preview(monitor_index: int):
        data = service.get_monitor_preview(monitor_index)
        return jsonify(data)

    @app.post("/api/monitors/select")
    def update_monitor():
        payload = request.get_json(silent=True) or {}
        monitor_index = int(payload.get("monitor_index", 1))
        result = service.update_monitor(monitor_index)
        code = 200 if result.get("ok") else 400
        return jsonify(result), code

    @app.post("/api/start")
    def start():
        payload = request.get_json(silent=True) or {}
        result = service.start(
            payload.get("start_time", ""),
            payload.get("end_time", ""),
            payload.get("interval_s"),
            payload.get("categories"),
            payload.get("tree_id", ""),
        )
        code = 200 if result.get("ok") else 400
        return jsonify(result), code

    @app.post("/api/stop")
    def stop():
        return jsonify(service.stop())

    @app.post("/api/manual")
    def manual():
        try:
            payload = request.get_json(silent=True) or {}
            result = service.manual_record(tree_id=payload.get("tree_id", ""))
            code = 200 if result.get("ok") else 400
            return jsonify(result), code
        except Exception as exc:
            return jsonify(
                {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
            ), 500

    @app.post("/api/tree/create")
    def tree_create():
        payload = request.get_json(silent=True) or {}
        try:
            result = service.create_tree(
                date_text=payload.get("date", ""),
                name=payload.get("name", ""),
            )
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @app.post("/api/tree/delete")
    def tree_delete():
        payload = request.get_json(silent=True) or {}
        try:
            result = service.delete_tree(
                date_text=payload.get("date", ""),
                tree_id=payload.get("tree_id", ""),
            )
            code = 200 if result.get("ok") else 400
            return jsonify(result), code
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @app.post("/api/preferences")
    def preferences():
        payload = request.get_json(silent=True) or {}
        try:
            result = service.set_preferences(
                interval_s=payload.get("interval_s"),
                categories=payload.get("categories"),
            )
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @app.get("/api/tree")
    def tree():
        date_text = request.args.get("date", "").strip()
        tree_id = request.args.get("tree_id", "").strip()
        try:
            data = service.tree_data(date_text=date_text, tree_id=tree_id)
            return jsonify({"ok": True, "data": data})
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @app.get("/api/cards")
    def cards():
        date_text = request.args.get("date", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        search = request.args.get("search", "").strip()
        sort = request.args.get("sort", "time_desc").strip() or "time_desc"
        categories = _parse_list_arg("categories")
        tree_ids = _parse_list_arg("tree_ids")
        try:
            page = int(request.args.get("page", "1").strip() or "1")
            page_size = int(request.args.get("page_size", "50").strip() or "50")
        except ValueError:
            return jsonify(
                {"ok": False, "message": "page/page_size must be integers"}
            ), 400
        try:
            data = service.cards_data(
                date_text=date_text,
                date_from=date_from,
                date_to=date_to,
                categories=categories or None,
                tree_ids=tree_ids or None,
                search=search,
                page=page,
                page_size=page_size,
                sort=sort,
            )
            return jsonify({"ok": True, "data": data})
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception as exc:
            return jsonify(
                {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
            ), 500

    @app.put("/api/cards/<card_id>")
    def update_card(card_id: str):
        payload = request.get_json(silent=True) or {}
        try:
            result = service.update_card(
                card_id=card_id,
                summary=payload.get("summary"),
                category=payload.get("category"),
            )
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception as exc:
            return jsonify(
                {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
            ), 500

    @app.delete("/api/cards/<card_id>")
    def delete_card(card_id: str):
        try:
            result = service.delete_card(card_id=card_id)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception as exc:
            return jsonify(
                {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
            ), 500

    @app.post("/api/cards/export")
    def export_cards():
        payload = request.get_json(silent=True) or {}
        export_format = str(payload.get("format", "markdown") or "markdown")
        filters = payload.get("filters")
        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            return jsonify({"ok": False, "message": "filters must be object"}), 400
        try:
            content, filename = service.export_cards(
                format=export_format,
                filters=filters,
            )
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext == "json":
                mimetype = "application/json; charset=utf-8"
            elif ext == "csv":
                mimetype = "text/csv; charset=utf-8"
            else:
                mimetype = "text/markdown; charset=utf-8"
            response = Response(content, mimetype=mimetype)
            response.headers["Content-Disposition"] = (
                f'attachment; filename="{filename}"'
            )
            return response
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception as exc:
            return jsonify(
                {"ok": False, "message": f"{type(exc).__name__}: {exc}"}
            ), 500

    @app.get("/api/daily-summary")
    def daily_summary():
        date_text = request.args.get("date", "").strip()
        try:
            data = service.daily_summary_cached(date_text)
            if data is None:
                return (
                    jsonify({"error": "no_data", "message": "该日期无活动记录"}),
                    404,
                )
            return jsonify(data), 200
        except ValueError as exc:
            return (
                jsonify({"error": "invalid_request", "message": str(exc)}),
                400,
            )
        except Exception as exc:
            return (
                jsonify(
                    {
                        "error": "internal_error",
                        "message": f"{type(exc).__name__}: {exc}",
                    }
                ),
                500,
            )

    @app.post("/api/daily-summary/generate")
    def generate_daily_summary():
        payload = request.get_json(silent=True) or {}
        date_text = str(payload.get("date", "") or "").strip()
        force = bool(payload.get("force", False))
        try:
            data = service.daily_summary(date_text, force=force)
            return jsonify(data), 200
        except ValueError as exc:
            if str(exc) == "no_data":
                return (
                    jsonify({"error": "no_data", "message": "该日期无活动记录"}),
                    404,
                )
            return (
                jsonify({"error": "invalid_request", "message": str(exc)}),
                400,
            )
        except Exception as exc:
            return (
                jsonify(
                    {
                        "error": "internal_error",
                        "message": f"{type(exc).__name__}: {exc}",
                    }
                ),
                500,
            )

    @app.get("/api/daily-summary/stream")
    def stream_daily_summary():
        date_text = request.args.get("date", "").strip()
        force = _parse_bool_arg(request.args.get("force"), default=False)

        def stream():
            try:
                for event, payload in service.daily_summary_stream(
                    date_text, force=force
                ):
                    yield _sse_event(event, payload)
            except ValueError as exc:
                message = "该日期无活动记录" if str(exc) == "no_data" else str(exc)
                yield _sse_event("error", {"message": message, "error": str(exc)})
            except Exception as exc:
                yield _sse_event(
                    "error",
                    {
                        "message": f"{type(exc).__name__}: {exc}",
                        "error": "internal_error",
                    },
                )

        response = Response(stream(), mimetype="text/event-stream")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    @app.get("/api/logs")
    def logs():
        try:
            lines = int(request.args.get("lines", "120"))
        except ValueError:
            lines = 120
        date_text = request.args.get("date", "").strip()
        try:
            data = service.logs(lines=lines, date_text=date_text)
            return jsonify({"ok": True, "data": data})
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    return app
