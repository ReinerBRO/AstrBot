# 日志卡片视图 API 文档

更新时间：2026-02-11

## 1. 获取卡片列表

- 方法：`GET /api/cards`
- 说明：按日期/分类/树/关键词筛选卡片，支持分页与排序。

### Query 参数

- `date`：单日，格式 `YYYY-MM-DD`
- `date_from`：起始日期，格式 `YYYY-MM-DD`
- `date_to`：结束日期，格式 `YYYY-MM-DD`
- `categories`：分类过滤，可多值或逗号分隔（如 `categories=写代码,研究`）
- `tree_ids`：树过滤，可多值或逗号分隔
- `search`：全文搜索关键词
- `page`：页码，默认 `1`
- `page_size`：每页数量，默认 `50`，最大 `500`
- `sort`：`time_desc` 或 `time_asc`，默认 `time_desc`

### 响应示例

```json
{
  "ok": true,
  "data": {
    "cards": [
      {
        "id": "20260211-0941-001",
        "time": "09:41",
        "date": "2026-02-11",
        "category": "写代码",
        "summary": "正在启动工作追踪系统",
        "tree_id": "tree-abc",
        "tree_name": "Morning Tree",
        "source": "vl+event",
        "confidence": 0.62,
        "vl_category": "写代码",
        "event_category": "研究",
        "event_data": {
          "click_count": 0,
          "top_app": "",
          "active_seconds": 0
        }
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50,
    "has_more": false,
    "stats": {
      "total_count": 1,
      "category_counts": {
        "写代码": 1
      },
      "total_active_seconds": 0,
      "avg_interval_seconds": 0,
      "date_range": {
        "start": "2026-02-11",
        "end": "2026-02-11"
      }
    }
  }
}
```

### 错误

- `400`：参数格式错误（如日期、分页、排序值非法）
- `500`：服务内部错误

## 2. 更新卡片

- 方法：`PUT /api/cards/<card_id>`
- 说明：更新卡片摘要和/或分类。

### Path 参数

- `card_id`：格式 `YYYYMMDD-HHMM-序号`，例如 `20260211-0941-001`

### Body

```json
{
  "summary": "更新后的摘要",
  "category": "研究"
}
```

### 响应示例

```json
{
  "ok": true,
  "message": "卡片已更新",
  "card": {
    "id": "20260211-0941-001",
    "time": "09:41",
    "date": "2026-02-11",
    "category": "研究",
    "summary": "更新后的摘要",
    "tree_id": "tree-abc",
    "tree_name": "Morning Tree",
    "source": "vl+event",
    "confidence": 0.62,
    "vl_category": "写代码",
    "event_category": "研究",
    "event_data": {
      "click_count": 0,
      "top_app": "",
      "active_seconds": 0
    }
  }
}
```

### 错误

- `400`：`card_id` 不合法、卡片不存在、分类不在允许列表、摘要为空
- `500`：服务内部错误

## 3. 删除卡片

- 方法：`DELETE /api/cards/<card_id>`
- 说明：删除指定卡片；如果该树在当日无剩余记录，会将树元数据标记为删除。

### 响应示例

```json
{
  "ok": true,
  "message": "卡片已删除",
  "card_id": "20260211-0941-001"
}
```

### 错误

- `400`：`card_id` 不合法或卡片不存在
- `500`：服务内部错误

## 4. 导出卡片

- 方法：`POST /api/cards/export`
- 说明：按筛选条件导出卡片文件。

### Body

```json
{
  "format": "markdown",
  "filters": {
    "date": "2026-02-11",
    "categories": ["写代码", "研究"],
    "tree_ids": ["tree-abc"],
    "search": "LLM",
    "sort": "time_desc"
  }
}
```

### 返回

- 成功时返回文件流，并设置 `Content-Disposition: attachment; filename="..."`。
- `format=markdown`：`text/markdown`
- `format=json`：`application/json`
- `format=csv`：`text/csv`

### 错误

- `400`：`format` 非法、`filters` 不是对象、筛选参数非法
- `500`：服务内部错误

