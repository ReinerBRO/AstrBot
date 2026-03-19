# 日志卡片视图 - Agent 分工方案

> 创建日期：2026-02-11
> 项目：Watcher 日志卡片视图
> 总工期：6-9 天

## 分工概览

| Agent | 职责 | 工期 | 依赖 |
|-------|------|------|------|
| **Agent A** | 后端 API 开发 | 2-3 天 | 无 |
| **Agent B** | 前端 UI 开发 | 3-4 天 | Agent A 完成 API |

## Agent A：后端 API 开发

### 职责范围
负责所有后端数据处理和 API 端点开发，为前端提供完整的数据接口。

### 工作内容

#### 阶段 1：数据层开发（1 天）

**文件**：`app/service.py`

**任务清单**：

1. **实现 `cards_data()` 方法**
   ```python
   def cards_data(
       self,
       date_text: str = "",
       date_from: str = "",
       date_to: str = "",
       categories: list[str] | None = None,
       tree_ids: list[str] | None = None,
       search: str = "",
       page: int = 1,
       page_size: int = 50,
       sort: str = "time_desc"
   ) -> dict:
       """
       获取卡片数据

       返回格式：
       {
           "cards": [...],
           "total": 42,
           "page": 1,
           "page_size": 50,
           "has_more": False,
           "stats": {...}
       }
       """
   ```

   **子任务**：
   - [ ] 解析报告文件（支持单日和日期范围）
   - [ ] 提取卡片数据（时间、分类、摘要、树 ID 等）
   - [ ] 实现分类筛选逻辑
   - [ ] 实现树 ID 筛选逻辑
   - [ ] 实现全文搜索（支持中英文）
   - [ ] 实现分页逻辑
   - [ ] 实现排序（时间升序/降序）
   - [ ] 计算统计信息（总数、分类分布、活跃时长）
   - [ ] 生成唯一卡片 ID（格式：`YYYYMMDD-HHMM-序号`）

2. **实现 `update_card()` 方法**
   ```python
   def update_card(
       self,
       card_id: str,
       summary: str | None = None,
       category: str | None = None
   ) -> dict:
       """
       更新卡片内容

       返回格式：
       {
           "ok": True,
           "message": "卡片已更新",
           "card": {...}
       }
       """
   ```

   **子任务**：
   - [ ] 解析卡片 ID，定位到报告文件的具体行
   - [ ] 验证分类是否在 `task_categories` 中
   - [ ] 更新报告文件中的对应行
   - [ ] 保持 Markdown 格式一致性
   - [ ] 返回更新后的卡片数据

3. **实现 `delete_card()` 方法**
   ```python
   def delete_card(self, card_id: str) -> dict:
       """
       删除卡片

       返回格式：
       {
           "ok": True,
           "message": "卡片已删除",
           "card_id": "20260207-0941-001"
       }
       """
   ```

   **子任务**：
   - [ ] 解析卡片 ID，定位到报告文件的具体行
   - [ ] 从报告文件中删除该行
   - [ ] 检查是否需要更新树元数据（如果该树没有其他记录）
   - [ ] 返回删除结果

4. **实现 `export_cards()` 方法**
   ```python
   def export_cards(
       self,
       format: str = "markdown",
       filters: dict | None = None
   ) -> tuple[str, str]:
       """
       导出卡片数据

       返回：(content, filename)
       """
   ```

   **子任务**：
   - [ ] 支持 Markdown 格式导出
   - [ ] 支持 JSON 格式导出
   - [ ] 支持 CSV 格式导出
   - [ ] 应用筛选条件（复用 `cards_data()` 的筛选逻辑）
   - [ ] 生成文件名（格式：`watcher-report-YYYYMMDD-YYYYMMDD.{ext}`）

#### 阶段 2：API 层开发（0.5 天）

**文件**：`app/web.py`

**任务清单**：

1. **添加 `GET /api/cards` 路由**
   ```python
   @app.get("/api/cards")
   def cards():
       # 解析查询参数
       # 调用 service.cards_data()
       # 返回 JSON 响应
   ```

   **子任务**：
   - [ ] 解析查询参数（date, date_from, date_to, categories, tree_ids, search, page, page_size, sort）
   - [ ] 处理参数验证和类型转换
   - [ ] 调用 `service.cards_data()`
   - [ ] 返回标准 JSON 响应格式
   - [ ] 错误处理（400, 500）

2. **添加 `PUT /api/cards/<card_id>` 路由**
   ```python
   @app.put("/api/cards/<card_id>")
   def update_card(card_id):
       # 解析请求体
       # 调用 service.update_card()
       # 返回 JSON 响应
   ```

   **子任务**：
   - [ ] 解析请求体（summary, category）
   - [ ] 参数验证
   - [ ] 调用 `service.update_card()`
   - [ ] 返回更新后的卡片数据
   - [ ] 错误处理

3. **添加 `DELETE /api/cards/<card_id>` 路由**
   ```python
   @app.delete("/api/cards/<card_id>")
   def delete_card(card_id):
       # 调用 service.delete_card()
       # 返回 JSON 响应
   ```

   **子任务**：
   - [ ] 调用 `service.delete_card()`
   - [ ] 返回删除结果
   - [ ] 错误处理

4. **添加 `POST /api/cards/export` 路由**
   ```python
   @app.post("/api/cards/export")
   def export_cards():
       # 解析请求体
       # 调用 service.export_cards()
       # 返回文件下载响应
   ```

   **子任务**：
   - [ ] 解析请求体（format, filters）
   - [ ] 调用 `service.export_cards()`
   - [ ] 设置正确的 Content-Type 和 Content-Disposition
   - [ ] 返回文件下载响应
   - [ ] 错误处理

#### 阶段 3：测试（0.5-1 天）

**文件**：`tests/test_cards_api.py`, `tests/test_cards_service.py`

**任务清单**：

1. **单元测试**
   - [ ] 测试 `cards_data()` 的各种筛选组合
   - [ ] 测试分页逻辑（边界情况）
   - [ ] 测试搜索功能（中英文、特殊字符）
   - [ ] 测试 `update_card()` 的验证逻辑
   - [ ] 测试 `delete_card()` 的边界情况
   - [ ] 测试 `export_cards()` 的各种格式

2. **集成测试**
   - [ ] 测试 API 端点的完整流程
   - [ ] 测试错误处理（400, 404, 500）
   - [ ] 测试并发请求（如果需要）

3. **性能测试**
   - [ ] 测试大数据量（1000+ 条记录）的查询性能
   - [ ] 测试搜索性能
   - [ ] 测试导出性能

### 交付物

1. **代码**：
   - `app/service.py`（新增 4 个方法）
   - `app/web.py`（新增 4 个路由）
   - `tests/test_cards_api.py`（新文件）
   - `tests/test_cards_service.py`（新文件）

2. **文档**：
   - API 文档（Markdown 格式）
   - 数据格式说明
   - 测试报告

3. **测试覆盖率**：
   - 目标：> 80%
   - 所有测试通过

### 验收标准

- [ ] 所有 API 端点正常工作
- [ ] 筛选、搜索、分页功能正确
- [ ] 编辑、删除功能正确
- [ ] 导出功能支持 3 种格式
- [ ] 统计信息准确
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试全部通过
- [ ] 性能测试达标（查询 < 500ms）
- [ ] 代码符合项目规范（PEP 8）
- [ ] API 文档完整

---

## Agent B：前端 UI 开发

### 职责范围
负责所有前端界面和交互开发，实现卡片视图的完整用户体验。

### 前置条件
- Agent A 完成后端 API 开发
- API 文档可用
- 可以调用测试 API

### 工作内容

#### 阶段 1：基础组件开发（1.5 天）

**文件**：`app/web_static/`

**任务清单**：

1. **创建 `ViewSwitcher.js`**
   ```javascript
   class ViewSwitcher {
       constructor(container, onViewChange) {
           // 视图切换器组件
       }

       setActiveView(view) {
           // 设置当前视图
       }
   }
   ```

   **子任务**：
   - [ ] 实现视图切换按钮（树视图、卡片视图、日志）
   - [ ] 高亮当前选中视图
   - [ ] 触发视图切换事件
   - [ ] URL 参数同步（`?view=cards`）
   - [ ] localStorage 记住用户选择

2. **创建 `CardView.js`**
   ```javascript
   class CardView {
       constructor(container) {
           // 卡片视图主组件
       }

       async loadCards(filters) {
           // 加载卡片数据
       }

       render() {
           // 渲染卡片列表
       }
   }
   ```

   **子任务**：
   - [ ] 实现卡片视图容器
   - [ ] 调用 `/api/cards` 获取数据
   - [ ] 渲染卡片列表
   - [ ] 处理加载状态
   - [ ] 处理错误状态
   - [ ] 处理空状态

3. **创建 `Card.js`**
   ```javascript
   class Card {
       constructor(data, onEdit, onDelete, onCopy) {
           // 单个卡片组件
       }

       render() {
           // 渲染卡片 HTML
       }
   }
   ```

   **子任务**：
   - [ ] 实现卡片布局（时间、分类、摘要、元数据）
   - [ ] 实现分类标签样式（不同颜色）
   - [ ] 实现操作按钮（复制、编辑、删除、查看树）
   - [ ] 实现编辑模式（内联编辑）
   - [ ] 实现删除确认对话框
   - [ ] 实现复制到剪贴板功能

4. **创建 `FilterBar.js`**
   ```javascript
   class FilterBar {
       constructor(container, onFilterChange) {
           // 筛选栏组件
       }

       getFilters() {
           // 获取当前筛选条件
       }
   }
   ```

   **子任务**：
   - [ ] 实现日期选择器（单日、范围、快捷选项）
   - [ ] 实现分类筛选（多选、显示数量）
   - [ ] 实现树筛选（下拉选择）
   - [ ] 实现搜索框（防抖 300ms）
   - [ ] 实现"重置筛选"按钮
   - [ ] 触发筛选变化事件

5. **创建 `StatsPanel.js`**
   ```javascript
   class StatsPanel {
       constructor(container) {
           // 统计面板组件
       }

       update(stats) {
           // 更新统计信息
       }
   }
   ```

   **子任务**：
   - [ ] 实现统计信息展示（总数、分类分布、活跃时长）
   - [ ] 实现折叠/展开功能
   - [ ] 实现分类占比可视化（简单进度条）
   - [ ] 格式化时长显示（6.5h）

6. **创建 `Pagination.js`**
   ```javascript
   class Pagination {
       constructor(container, onPageChange) {
           // 分页组件
       }

       update(page, total, pageSize) {
           // 更新分页状态
       }
   }
   ```

   **子任务**：
   - [ ] 实现分页按钮（上一页、下一页、页码）
   - [ ] 实现"加载更多"模式（可选）
   - [ ] 显示当前页和总页数
   - [ ] 触发页码变化事件

#### 阶段 2：样式开发（0.5 天）

**文件**：`app/web_static/style.css`

**任务清单**：

1. **视图切换器样式**
   - [ ] 按钮样式（默认、选中、hover）
   - [ ] 图标样式
   - [ ] 响应式布局

2. **卡片样式**
   - [ ] 卡片容器样式（边框、阴影、圆角）
   - [ ] 卡片内容布局（Flexbox/Grid）
   - [ ] 分类标签样式（彩色徽章）
   - [ ] 操作按钮样式
   - [ ] 编辑模式样式
   - [ ] hover 效果
   - [ ] 动画效果（进入、退出）

3. **筛选栏样式**
   - [ ] 筛选器布局（Flexbox）
   - [ ] 输入框样式
   - [ ] 下拉菜单样式
   - [ ] 按钮样式

4. **统计面板样式**
   - [ ] 面板布局
   - [ ] 统计项样式
   - [ ] 进度条样式
   - [ ] 折叠动画

5. **分页样式**
   - [ ] 分页按钮样式
   - [ ] 页码显示样式

6. **主题支持**
   - [ ] Dark 主题样式
   - [ ] Light 主题样式
   - [ ] 主题切换过渡

7. **响应式设计**
   - [ ] 桌面端（>1024px）：双列卡片
   - [ ] 平板端（768px-1024px）：单列卡片
   - [ ] 移动端（<768px）：紧凑卡片

#### 阶段 3：交互逻辑开发（1 天）

**文件**：`app/web_static/app.js`

**任务清单**：

1. **视图切换逻辑**
   - [ ] 初始化视图切换器
   - [ ] 处理视图切换事件
   - [ ] 显示/隐藏对应视图
   - [ ] URL 参数同步
   - [ ] localStorage 持久化

2. **筛选器状态管理**
   - [ ] 初始化筛选器
   - [ ] 监听筛选变化事件
   - [ ] 触发卡片数据重新加载
   - [ ] URL 参数同步（支持分享链接）

3. **搜索功能**
   - [ ] 实现搜索防抖（300ms）
   - [ ] 高亮匹配文本
   - [ ] 显示搜索结果数量

4. **分页逻辑**
   - [ ] 监听页码变化事件
   - [ ] 加载对应页数据
   - [ ] 滚动到顶部

5. **卡片操作**
   - [ ] 实现复制功能（Clipboard API）
   - [ ] 实现编辑功能（调用 `PUT /api/cards/<id>`）
   - [ ] 实现删除功能（调用 `DELETE /api/cards/<id>`）
   - [ ] 实现"查看树"功能（跳转到树视图并定位）

6. **导出功能**
   - [ ] 实现导出按钮
   - [ ] 选择导出格式（Markdown、JSON、CSV）
   - [ ] 调用 `POST /api/cards/export`
   - [ ] 触发文件下载

7. **批量操作**（可选）
   - [ ] 实现卡片多选
   - [ ] 批量删除
   - [ ] 批量导出

#### 阶段 4：集成与优化（1 天）

**任务清单**：

1. **集成到主应用**
   - [ ] 修改 `app/web_static/index.html`，添加视图切换器
   - [ ] 修改 `app/web_static/app.js`，集成卡片视图
   - [ ] 确保与现有树视图、日志视图共存
   - [ ] 测试视图切换流程

2. **性能优化**
   - [ ] 实现虚拟滚动（如果数据量大）
   - [ ] 优化搜索性能（前端缓存）
   - [ ] 优化渲染性能（DocumentFragment）
   - [ ] 图片懒加载（如果添加截图功能）

3. **用户体验优化**
   - [ ] 添加加载动画（Skeleton Screen）
   - [ ] 添加错误提示（Toast）
   - [ ] 添加空状态提示
   - [ ] 添加操作成功提示
   - [ ] 实现快捷键（Ctrl+F 搜索、Ctrl+E 导出）

4. **浏览器兼容性**
   - [ ] 测试 Chrome
   - [ ] 测试 Firefox
   - [ ] 测试 Safari
   - [ ] 测试 Edge

5. **移动端测试**
   - [ ] 测试 iOS Safari
   - [ ] 测试 Android Chrome
   - [ ] 测试触摸交互

### 交付物

1. **代码**：
   - `app/web_static/ViewSwitcher.js`（新文件）
   - `app/web_static/CardView.js`（新文件）
   - `app/web_static/Card.js`（新文件）
   - `app/web_static/FilterBar.js`（新文件）
   - `app/web_static/StatsPanel.js`（新文件）
   - `app/web_static/Pagination.js`（新文件）
   - `app/web_static/style.css`（修改）
   - `app/web_static/app.js`（修改）
   - `app/web_static/index.html`（修改）

2. **文档**：
   - 组件使用说明
   - 交互流程图
   - 样式指南

3. **测试**：
   - 手动测试报告
   - 浏览器兼容性报告
   - 移动端测试报告

### 验收标准

- [ ] 视图切换功能正常
- [ ] 卡片视图完整展示
- [ ] 筛选、搜索、分页功能正常
- [ ] 编辑、删除、复制功能正常
- [ ] 导出功能正常
- [ ] 统计信息准确
- [ ] Dark/Light 主题支持
- [ ] 响应式设计（桌面/平板/移动）
- [ ] 无明显 UI 卡顿
- [ ] 浏览器兼容性良好
- [ ] 代码符合项目规范
- [ ] 文档完整

---

## 协作流程

### 1. 启动阶段
- Agent A 和 Agent B 同时阅读实现计划文档
- Agent A 开始后端开发
- Agent B 准备前端开发环境，设计组件结构

### 2. 开发阶段
- **Day 1-2**：Agent A 完成数据层和 API 层
- **Day 2**：Agent A 提供 API 文档给 Agent B
- **Day 2-3**：Agent B 开始前端开发（可以使用 mock 数据）
- **Day 3**：Agent A 完成测试，Agent B 切换到真实 API
- **Day 4-5**：Agent B 完成前端开发和集成

### 3. 联调阶段
- Agent A 和 Agent B 一起测试完整流程
- 修复集成问题
- 性能优化

### 4. 验收阶段
- 运行所有测试
- 检查验收标准
- 准备交付

## 沟通机制

### 日常沟通
- 每日同步进度（15 分钟）
- 及时沟通阻塞问题
- 共享开发日志

### 文档共享
- Agent A 提供 API 文档（Markdown）
- Agent B 提供组件文档（Markdown）
- 共享测试报告

### 问题升级
- 技术问题：先尝试自行解决，超过 2 小时升级
- 需求问题：立即升级，共同讨论
- 性能问题：共同分析，协作优化

## 风险管理

### Agent A 风险
- **风险**：数据解析逻辑复杂，可能超时
- **缓解**：优先实现核心功能，复杂筛选后续迭代

### Agent B 风险
- **风险**：等待 API 完成，可能延误
- **缓解**：使用 mock 数据先行开发，API 完成后切换

### 共同风险
- **风险**：集成时发现接口不匹配
- **缓解**：提前定义清晰的接口规范，频繁沟通

## 总结

通过清晰的分工和协作机制，两个 Agent 可以并行开发，最大化效率。Agent A 专注后端数据和 API，Agent B 专注前端 UI 和交互，最终集成为完整的卡片视图功能。
