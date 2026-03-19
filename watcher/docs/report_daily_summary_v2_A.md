# report_daily_summary_v2_A

## Agent
A（后端流式能力）

## 实现目标
根据 `docs/日报总结V2_实现计划.md` 的 Agent A 任务，完成日报总结流式生成（SSE）后端实现，并补充测试。

## 已完成内容
1. 新增日报流式生成能力（LLM streaming + 降级）
- 文件：`watcher/daily_summary.py`
- 新增 `stream_llm_summary(entries, stats, config)`：
  - 优先使用 OpenAI Chat Completions `stream=true`，逐行解析 `data: {...}`。
  - 逐 token `yield` 文本片段。
  - streaming 不可用时自动降级为一次性生成，并单次输出。
- 复用并抽取了日报提示词与结果解析逻辑，保持与原有 `generate_llm_summary` 一致的兜底策略。

2. 新增 Service 层流式编排
- 文件：`app/service.py`
- 新增 `daily_summary_stream(date_str, force)`：
  - 缓存命中时输出 `("cached", payload)` 并结束。
  - 无缓存时按阶段输出：
    - `phase: parsing`
    - `phase: aggregating`
    - `phase: generating`
  - 生成过程中输出 `token` 事件。
  - 结束时输出 `highlights`、`segments`、`done`，并写入缓存。

3. 新增 SSE API 端点
- 文件：`app/web.py`
- 新增 `GET /api/daily-summary/stream?date=YYYY-MM-DD&force=false`
  - 响应类型：`text/event-stream`
  - 支持事件：`phase` / `token` / `highlights` / `segments` / `cached` / `done` / `error`
  - 处理 `force` 查询参数布尔值解析。

4. 新增/增强测试
- 文件：`tests/test_daily_summary.py`
- 新增用例覆盖：
  - `stream_llm_summary` 正常解析 SSE token。
  - `stream_llm_summary` streaming 失败降级。
  - `WatcherService.daily_summary_stream` 缓存短路。
  - `WatcherService.daily_summary_stream` 事件流顺序与缓存写入。
  - `/api/daily-summary/stream` SSE 输出格式。

## 验证结果
- `python -m compileall app watcher tests` 通过
- `PYTHONPATH=. pytest -q tests/test_daily_summary.py tests/test_cards_api.py tests/test_cards_service.py tests/test_report_parser.py tests/test_runner_integration.py` 通过（`29 passed`）

## 涉及文件
- `watcher/daily_summary.py`
- `app/service.py`
- `app/web.py`
- `tests/test_daily_summary.py`
- `docs/report_daily_summary_v2_A.md`
