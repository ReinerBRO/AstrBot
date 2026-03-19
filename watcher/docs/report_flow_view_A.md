# report_flow_view_A

## 任务范围
按 `docs/plan_flow_view.md` 的 Agent A 分工，实现 Flow 视图核心渲染文件：
- `app/web_static/FlowView.js`

本次只做 Agent A 职责，不包含 Agent B 的页面接入（`index.html / ViewSwitcher.js / app.js / flow-style.css`）。

## 已实现内容

### 1. FlowView 核心类与公开 API
文件：`app/web_static/FlowView.js`
- 新增 `FlowView` 类（`class FlowView`）。
- 完成公开方法：
  - `setData(entries, categories)`
  - `render()`
  - `resize()`
  - `setZoom(scale)`
  - `destroy()`
- 额外提供 `resetView()` 便于外部重置视图。

### 2. 数据处理与图结构构建
- 实现 `buildFlowGraph(entries, categories)`：
  - 对 entries 按时间排序（分钟级）
  - 构建节点 `nodes`（time/minute/category/summary/lane/x/y/color）
  - 构建边 `edges`，区分：
    - `same`（同泳道）
    - `switch`（跨泳道）
  - 计算相邻节点间隔分钟数，用于停留时长标注

### 3. 泳道布局与坐标映射
- 实现 `computeLaneX(categories)`：
  - 使用偏移模式实现左右分布（首类偏左、次类偏右、后续向外扩展）
- 实现时间到纵坐标映射与反算：
  - `minuteToY(minute)`
  - `yToMinute(y)`
- 实现 `updateNodeLayout()`：
  - 节点最小间距约束（防重叠）
  - 可见区裁剪缓存：`visibleNodeIndices` / `visibleEdgeIndices`

### 4. Canvas 分层绘制
- `drawTimeline(ctx)`：中线 + 小时/半小时刻度
- `drawLaneHeaders(ctx)`：泳道标题
- `drawEdges(ctx)`：同泳道直线、跨泳道贝塞尔曲线
- `drawDurationLabels(ctx)`：长间隔时长标签（如 `15m` / `1h 20m`）
- `drawSwitchLabels(ctx)`：跨泳道切换标签（`-> 目标分类`）
- `drawNodes(ctx)`：节点渲染 + 选中/悬停高亮 + 左侧时间文本

### 5. 交互能力
- `handleWheel(event)`：纵向缩放（锚点缩放）
- `handleMouseDown/Move/Up`：拖拽平移
- `hitTest(x, y)`：节点命中测试
- `handleMouseMove`：hover 触发外部 tooltip 回调
- `handleClick`：选中节点并回调 `onSelect`

## 验证结果
- `node --check app/web_static/FlowView.js` 通过
- `python -m compileall app watcher` 通过

## 交付文件
- `app/web_static/FlowView.js`
- `docs/report_flow_view_A.md`
