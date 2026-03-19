# report_logic_tree_A

## Agent
A（后端逻辑树）

## 目标
按 `docs/逻辑树_实现计划.md` 的 Agent A 范围，实现逻辑树构建算法、后端 API 集成、配置项与测试。

## 完成项
1. 新增逻辑树构建模块
- 文件：`watcher/tree_builder.py`
- 新增数据结构：
  - `TreeEntry`
  - `BranchNode`
- 新增核心函数：
  - `build_logical_tree(entries, gap_threshold=30)`
  - `tree_to_dict(node)`
  - `compute_tree_stats(node)`
- 规则已覆盖：
  - 同分类连续归同分支
  - 分类切换新建分支
  - 间隔大于阈值新建主干段

2. Service API 集成
- 文件：`app/service.py`
- `tree_data()` 新增返回字段：
  - `logical_tree`
  - `logical_tree_stats`
  - `tree_layout_mode`
- 同时保持原有字段（`entries`、`trees` 等）不变，向后兼容。
- `status()` 新增返回：
  - `tree_gap_threshold_min`
  - `tree_layout_mode`

3. 配置项扩展
- 文件：`watcher/config.py`
- `Config` 新增字段：
  - `tree_gap_threshold_min`
  - `tree_layout_mode`
- `load_config()` 新增环境变量读取：
  - `TREE_GAP_THRESHOLD_MIN`（默认 30，范围 5~240）
  - `TREE_LAYOUT_MODE`（`logical`/`classic`，默认 `logical`）

4. 测试
- 新增文件：`tests/test_tree_builder.py`
- 覆盖场景：
  - 空输入
  - 单分类连续
  - 分类切换
  - 长间隔新主干段
  - 混合场景统计
  - `WatcherService.tree_data()` 在 `logical/classic` 模式下行为
- 同步更新：
  - `tests/test_cards_service.py`（Config 新字段）
  - `tests/test_runner_integration.py`（Config 新字段）

## 验证
- `python -m compileall app watcher tests` 通过
- `PYTHONPATH=. pytest -q tests/test_tree_builder.py tests/test_cards_service.py tests/test_runner_integration.py tests/test_daily_summary.py tests/test_report_parser.py` 通过（`33 passed`）

## 涉及文件
- `watcher/tree_builder.py`
- `watcher/config.py`
- `app/service.py`
- `tests/test_tree_builder.py`
- `tests/test_cards_service.py`
- `tests/test_runner_integration.py`
- `docs/report_logic_tree_A.md`
