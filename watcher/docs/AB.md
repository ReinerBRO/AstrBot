# Agent A/B 实施记录

## 记录时间
- 2026-02-10

## 目标范围
- Agent A：事件采集模块（点击监听、窗口解析）
- Agent B：事件存储模块（事件缓冲、聚合、持久化）

## 已完成内容
- 实现点击事件监听器，支持启动/停止、回调上报、权限失败降级处理。
- 实现窗口信息解析器，支持获取前台应用、窗口标题、Bundle ID（macOS 优先）并提供回退行为。
- 实现事件数据模型：`ClickEvent`、`WindowInfo`、`AggregatedFeatures`。
- 实现事件缓冲器：内存保留最近窗口事件、按时间范围聚合点击数/应用切换/活跃时长/关键词/应用分布。
- 实现事件日志器：异步写入 JSONL，按日期滚动到 `logs/click-events-YYYY-MM-DD.jsonl`。
- 扩展配置项：事件源开关、隐私脱敏、缓冲窗口、触发阈值、融合权重、事件日志目录等。
- 补充单元测试，覆盖 A/B 模块核心路径与配置解析。

## 变更文件
- `watcher/event_source/__init__.py`
- `watcher/event_source/models.py`
- `watcher/event_source/click_listener.py`
- `watcher/event_source/window_resolver.py`
- `watcher/event_source/event_buffer.py`
- `watcher/event_source/event_logger.py`
- `watcher/config.py`
- `watcher/__init__.py`
- `requirements.txt`
- `tests/event_source/__init__.py`
- `tests/event_source/test_event_source.py`
- `tests/test_config_event_source.py`

## 验证记录
- `python -m compileall app watcher`：通过
- `python -m unittest discover -s tests -v`：通过（9/9）
