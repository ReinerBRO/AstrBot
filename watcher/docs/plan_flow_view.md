# Plan: Flow View（工作流视图）

## 目标

新增第四个视图 "Flow"，以 git-graph 风格展示活动的时间流动和分支切换。
用户一眼看到：什么时候在写代码、什么时候切到研究、停留多久、何时切回。

**不替代现有 Tree / Cards / Logs 视图，而是新增视图。**

---

## 视觉设计

```
  时间轴        写代码(左)      中线       研究(右)      娱乐(远右)
  09:15         ●━━━━━━━━━━━━━━┃
                               ┃
  09:32         ●━━━━━━━━━━━━━━┃
                               ┃
  09:48            ╲           ┃
                    ╲          ┃
  09:48              ┃━━━━━━━━━●        ← 切换到研究
                               ┃
  10:05              ┃━━━━━━━━━●
                    ╱          ┃
  10:20         ●━━╱━━━━━━━━━━━┃        ← 切回写代码
                               ┃
  10:35         ●━━━━━━━━━━━━━━┃
                               ┃
  10:52                        ┃━━━━━━━━━━━●  ← 切到娱乐
                               ┃
  11:10         ●━━━━━━━━━━━━━━┃        ← 切回写代码
```

### 核心元素

| 元素 | 说明 |
|------|------|
| 中线 | 垂直时间轴主干，从上到下代表时间流逝 |
| 泳道 | 每个分类一条纵向泳道，左右分布（写代码左、研究中右、娱乐远右） |
| 节点 | 圆点，代表一次活动记录，颜色对应分类 |
| 连线 | 相邻节点之间的连线：同泳道=直线，跨泳道=贝塞尔曲线（分支线） |
| 时间标签 | 左侧显示 HH:MM |
| 停留时长 | 节点之间的间距按实际时间比例缩放，长间隔处显示 "15min" 标签 |
| 切换标记 | 跨泳道连线旁显示 "→ 研究" 文字，标明切换方向 |

### 交互

- Hover 节点：显示 tooltip（时间、分类、摘要，复用现有 tooltip）
- 滚轮缩放：纵向缩放时间轴
- 拖拽平移：上下平移
- 点击节点：高亮该节点，显示详情

---

## 数据源

复用现有 `/api/tree` 接口返回的 `entries` 数组：

```json
{
  "time": "09:15",
  "category": "写代码",
  "summary": "在 VSCode 中编辑 app.js",
  "tree_id": "abc123"
}
```

不需要新增后端接口。Flow View 在前端对 entries 做排序和分组即可。

---

## 技术方案

### 新增文件

| 文件 | 职责 | Agent |
|------|------|-------|
| `app/web_static/FlowView.js` | Flow 视图核心类：数据处理 + Canvas 渲染 | Agent A |
| `app/web_static/flow-style.css` | Flow 视图专用样式（容器、工具栏） | Agent B |

### 修改文件

| 文件 | 改动 | Agent |
|------|------|-------|
| `app/web_static/index.html` | 添加 `#flowViewSection` 容器、引入 FlowView.js 和 flow-style.css | Agent B |
| `app/web_static/ViewSwitcher.js` | `VALID_VIEWS` 增加 `"flow"`，views 数组增加 Flow 选项 | Agent B |
| `app/web_static/app.js` | `setActiveView` 支持 `"flow"`，初始化 FlowView 实例，数据联动 | Agent B |

---

## Agent 分工

### Agent A — FlowView 核心渲染（FlowView.js）

负责 `FlowView` 类的完整实现：

**1. 数据处理层**
- `buildFlowGraph(entries, categories)` → 将 entries 转为有序节点列表
- 每个节点：`{ time, minute, category, summary, lane, x, y }`
- 每条边：`{ from, to, type: "same"|"switch" }`
- 泳道分配：按 category 映射到固定 lane 位置

**2. 布局计算**
- 纵轴：时间 → y 坐标（按分钟比例映射，支持缩放）
- 横轴：lane → x 坐标（固定泳道位置）
- 节点间距：最小间距保证，避免重叠
- 视口裁剪：只渲染可见区域内的节点和边

**3. Canvas 渲染**
- `drawTimeline(ctx)` — 绘制中线 + 时间刻度
- `drawLaneHeaders(ctx)` — 顶部泳道标签（写代码、研究、娱乐...）
- `drawEdges(ctx)` — 绘制连线（同泳道直线，跨泳道贝塞尔曲线）
- `drawNodes(ctx)` — 绘制节点圆点（带分类颜色）
- `drawSwitchLabels(ctx)` — 跨泳道切换处的 "→ 研究" 标签
- `drawDurationLabels(ctx)` — 长间隔处的时长标签（"15min"）

**4. 交互**
- 缩放（wheel）和平移（drag）— 复用 tree view 的 viewState 模式
- `hitTest(x, y)` — 判断鼠标是否在某节点上
- Hover → 调用 app.js 的 `showTooltip` 显示详情
- 节点选中高亮

**5. 公开 API**
```javascript
class FlowView {
  constructor(canvas, options)  // canvas 元素 + 配置
  setData(entries, categories)  // 设置数据
  render()                      // 重绘
  resize()                      // 响应容器尺寸变化
  setZoom(scale)                // 缩放
  destroy()                     // 清理事件监听
}
```

### Agent B — 集成与样式（ViewSwitcher + app.js + HTML + CSS）

**1. HTML 结构**（index.html）
- 在 `#logsViewSection` 之后添加：
```html
<section id="flowViewSection" class="card flow-card hidden" aria-live="polite">
  <div class="flow-toolbar">
    <span class="small-muted">Activity Flow</span>
    <div class="flow-controls">
      <button id="flowZoomOutBtn" class="btn btn-ghost" type="button">-</button>
      <button id="flowZoomInBtn" class="btn btn-ghost" type="button">+</button>
      <button id="flowResetBtn" class="btn btn-ghost reset-btn" type="button">Reset</button>
    </div>
  </div>
  <div class="flow-canvas-shell">
    <canvas id="flowCanvas" tabindex="0" role="img"
            aria-label="Activity flow visualization"></canvas>
  </div>
</section>
```

**2. ViewSwitcher 改造**（ViewSwitcher.js）
- `VALID_VIEWS` → `["tree", "cards", "flow", "logs"]`
- views 默认数组增加 `{ id: "flow", label: "Flow", icon: "🔀" }`

**3. app.js 集成**
- DOM 引用：`flowViewSection`, `flowCanvas`, `flowZoomInBtn`, `flowZoomOutBtn`, `flowResetBtn`
- `setActiveView` 增加 `"flow"` 分支：
  - 显示/隐藏 `flowViewSection`
  - 调用 `flowView.setData(lastTreeData.entries, uiState.categories)` + `flowView.render()`
- `initCardsView` 中（或新函数 `initFlowView`）实例化 FlowView
- `refreshTree` 后如果当前是 flow 视图，刷新 flow 数据
- 缩放/重置按钮事件绑定

**4. 样式**（flow-style.css）
- `.flow-card` — 容器样式（复用 tree-card 模式）
- `.flow-toolbar` — 工具栏（flex 布局）
- `.flow-canvas-shell` — canvas 容器（高度 calc，border-radius，overflow hidden）
- `.flow-controls` — 缩放按钮组
- 响应式适配（复用现有断点）

---

## 实现顺序

```
Phase 1: Agent A + Agent B 并行
  ├─ Agent A: FlowView.js（数据处理 + 布局 + 渲染 + 交互）
  └─ Agent B: HTML + CSS + ViewSwitcher + app.js 集成骨架

Phase 2: 联调
  ├─ Agent B 引入 FlowView.js，绑定数据流
  └─ 验证：切换到 Flow 视图能正确渲染

Phase 3: 打磨
  ├─ 动画过渡（节点淡入、连线绘制动画）
  └─ 边界情况（无数据、单条数据、全部同分类）
```

---

## 约束

- 不新增后端接口，纯前端实现
- 不引入外部库，纯 Canvas 2D
- 复用现有 tooltip、颜色体系（COLOR_PALETTE、CSS 变量）
- 复用现有缩放/平移交互模式
- 保持所有现有测试通过
