# 日志卡片视图 Agent A 交付记录

交付日期：2026-02-11

## 1. 交付范围

已完成 Agent A 要求的后端工作：

- `cards_data()`：卡片查询（筛选、搜索、排序、分页、统计）
- `update_card()`：卡片编辑（摘要/分类）
- `delete_card()`：卡片删除（含孤儿树元数据处理）
- `export_cards()`：卡片导出（Markdown/JSON/CSV）
- 新增 4 个 API 路由
- 新增服务层与 API 层测试
- 补齐 API 文档、数据格式文档、测试报告

## 2. 代码变更

### 2.1 Service

- 文件：`app/service.py`
- 新增方法：
  - `_resolve_cards_dates()`
  - `_tree_name_map_for_date()`
  - `_collect_cards_for_date()`
  - `_cards_data_impl()`
  - `cards_data()`
  - `update_card()`
  - `delete_card()`
  - `export_cards()`
- 新增能力：
  - 卡片 ID 解析（`YYYYMMDD-HHMM-序号`）
  - 报告元信息解析（`source/vl/event/reason`）
  - 统计信息生成（分类分布、活跃时长、平均间隔、日期范围）

### 2.2 Web API

- 文件：`app/web.py`
- 新增路由：
  - `GET /api/cards`
  - `PUT /api/cards/<card_id>`
  - `DELETE /api/cards/<card_id>`
  - `POST /api/cards/export`
- 包含参数校验、错误处理与导出下载响应头设置。

## 3. 接口清单

### 3.1 GET /api/cards

支持参数：

- `date` / `date_from` / `date_to`
- `categories`
- `tree_ids`
- `search`
- `page` / `page_size`
- `sort`（`time_desc|time_asc`）

返回：

- `cards`、`total`、`page`、`page_size`、`has_more`、`stats`

### 3.2 PUT /api/cards/<card_id>

请求体：

- `summary`（可选）
- `category`（可选）

### 3.3 DELETE /api/cards/<card_id>

按卡片 ID 删除记录，必要时将对应树标记为删除。

### 3.4 POST /api/cards/export

请求体：

- `format`：`markdown|json|csv`
- `filters`：同查询参数语义

返回：

- 文件流 + `Content-Disposition: attachment; filename="..."`

## 4. 测试交付

### 4.1 新增测试文件

- `tests/test_cards_service.py`
- `tests/test_cards_api.py`

### 4.2 覆盖点

- 筛选/搜索/排序/分页
- 卡片编辑与分类校验
- 卡片删除与树元数据联动
- 三种导出格式
- API 参数错误处理与下载响应

### 4.3 验证结果

- `python -m unittest discover -s tests -v`：通过（32/32）
- `python -m compileall app watcher`：通过

## 5. 文档交付

- `docs/日志卡片视图_API文档.md`
- `docs/日志卡片视图_数据格式说明.md`
- `docs/日志卡片视图_测试报告.md`

## 6. 给 Agent B 的对接说明

- 前端直接对接 `/api/cards`、`/api/cards/<card_id>`、`/api/cards/export`。
- `cards[].id` 作为编辑/删除唯一标识。
- `cards[].source` 可用于显示来源标签（`vl` / `event` / `vl+event`）。
- 当前 `event_data` 为占位结构，前端应容错处理空值与 0 值。
