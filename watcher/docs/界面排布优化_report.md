# 界面排布优化_report

## 任务目标
根据 `docs/界面排布优化计划.md`，完成以下目标：
- 合并顶部区域（标题、视图切换、状态）为紧凑顶栏。
- 树视图控件压缩为单行工具栏。
- 移除常驻左侧栏，树画布改为全宽。
- 新增底部快捷操作栏（Start / Manual / Stop + 时间范围）。
- 将低频控制项改为可开关的设置抽屉。

## 实际改动

### 1) 页面结构重组
文件：`app/web_static/index.html`
- 移除原 `hero` 和独立 `viewSwitcher` 行，新增 `top-bar`：
  - 左：品牌信息
  - 中：`#viewSwitcherMount`
  - 右：`#statusBadge`、`#settingsToggleBtn`、`#themeToggleBtn`
- 树区域改为 `tree-toolbar` 单行结构，整合：
  - 日期选择（`#dateDropdownBtn` / `#dateDropdownMenu`）
  - 树选择（`#treeSelect`）
  - 树操作（`#newTreeBtn` / `#deleteTreeBtn` / `#reloadHistoryBtn`）
  - 分支筛选（`#branchFilters`）
  - 缩放控制（`#zoomOutBtn` / `#zoomInBtn` / `#resetViewBtn`）
- Start/Manual/Stop 按钮从侧栏迁移到底栏 `bottom-bar`，保留原 ID：
  - `#startBtn` / `#manualBtn` / `#stopBtn`
- `#rangeLabel` 迁移到底栏右侧。
- 原控制面板改为抽屉：`#settingsDrawer`，新增遮罩 `#settingsOverlay` 和关闭按钮 `#settingsCloseBtn`。
- 低频设置项（时间窗口、间隔、显示器、分类）都保留原 ID，避免 JS 绑定回归。

### 2) 样式与布局改造
文件：`app/web_static/style.css`
- 新增顶栏样式：`top-bar`（sticky, compact）。
- `workspace` 改为单列，树画布全宽。
- 新增单行树工具栏样式：`tree-toolbar` + `toolbar-group-*`。
- 画布高度策略改为基于视口计算：`tree-canvas-shell` 使用 `calc(100dvh - ...)`。
- 新增底栏样式：`bottom-bar`（sticky）。
- 新增抽屉与遮罩样式：`settings-drawer` / `settings-overlay`。
- 增加响应式规则（1320 / 820 / 520 断点），在移动端自动折行与按钮自适配。

### 3) 抽屉交互逻辑
文件：`app/web_static/app.js`
- 新增 DOM 引用：
  - `settingsToggleBtn`、`settingsCloseBtn`、`settingsDrawer`、`settingsOverlay`
- 在 `uiState` 中新增 `settingsOpen`。
- 新增 `setSettingsOpen(open)`：
  - 控制抽屉开关类名
  - 同步 `aria-hidden` / `aria-expanded`
  - 控制遮罩显隐
  - 控制 `body.drawer-open`
- 事件绑定：
  - 点击齿轮打开/关闭抽屉
  - 点击关闭按钮关闭抽屉
  - 点击遮罩关闭抽屉
  - `Esc` 同时支持关闭日期下拉与设置抽屉
- `boot()` 中初始化 `setSettingsOpen(false)`。

## 校验结果
- `node --check app/web_static/app.js`：通过。
- `python -m compileall app watcher`：通过。

## 本次不改动范围
- Tree Canvas 绘制主逻辑（`draw*` 流程）
- Cards / Logs 的内部数据流与 API 行为
- 后端接口与数据结构

## 输出文件
- `app/web_static/index.html`
- `app/web_static/style.css`
- `app/web_static/app.js`
- `docs/界面排布优化_report.md`
