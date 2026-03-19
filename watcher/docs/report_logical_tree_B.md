# report_logical_tree_B

## 角色与任务
- Agent: B（前端）
- 任务来源: `docs/逻辑树_实现计划.md` 中 3.2（逻辑树布局 + 渲染 + 交互）

## 本次实现范围

### 1. 逻辑树布局引擎（app.js）
- 新增布局主链：
  - `buildLogicalLayout(logicalTree, metrics, width, height)`
  - `assignBranchDirections(trunkSegment, existingBranches)`
  - `layoutBranchNodes(branch, startX, startY, direction, angle, width, metrics)`
- 新增场景构建：
  - `buildLogicalTreeScene(data, width, height, metrics)`
  - `buildTreeScene(...)` 改为逻辑模式优先、经典模式回退
  - 经典构建保留为 `buildClassicTreeScene(...)`
- 逻辑:
  - 主干段按 `logical_tree.children` 分段
  - 分支左右分配（含同类偏好 + 碰撞规避）
  - 叶子节点沿分支曲线布局
  - 支持 `trimmedCategories` 过滤

### 2. 逻辑树渲染（app.js）
- 新增渲染函数：
  - `drawLogicalTrunk(...)`
  - `drawBranchConnector(...)`
  - `drawBranchLabel(...)`
  - `drawLogicalNode(...)`
  - `findLogicalLabelAtPoint(...)`
- 在 `renderTreeFrame` 中新增分支：
  - `activeScene.renderMode === "logical"` 走逻辑树渲染
  - 否则沿用经典树渲染（完全兼容）

### 3. 交互实现（app.js）
- 节点交互：
  - 点击节点高亮所属分支（`selectedLogicalBranchId`）
  - 悬停节点继续使用现有 tooltip（时间/分类/摘要）
- 分支标签交互：
  - 点击标签折叠/展开分支（`collapsedLogicalBranchIds`）
- 画布行为：
  - 复用现有缩放/平移逻辑
  - 新增逻辑树标签命中与 hover 光标状态

### 4. 模式切换（逻辑/经典）
- 新增 UI 控件：`#treeLayoutModeSelect`（Logical / Classic）
- 前端状态：`uiState.treeLayoutMode`
- 新增方法：
  - `normalizeTreeLayoutMode(...)`
  - `setTreeLayoutMode(...)`
- 持久化：`localStorage[watcher_tree_layout_mode]`
- 切换日期/树时清理折叠与高亮状态，避免跨树污染

### 5. 页面与样式
- `index.html`：树工具栏新增 Layout 下拉
- `style.css`：新增 `layout-mode-field` 样式，适配现有工具栏体系

### 6. 版本号
- `app.js` UI build 更新为 `20260213-logical-tree-b1`
- `index.html` 中 `style.css` / `app.js` 资源版本同步更新

## 修改文件
- `app/web_static/app.js`
- `app/web_static/index.html`
- `app/web_static/style.css`

## 校验结果
- `node --check app/web_static/app.js` ✅
- `python -m compileall app watcher` ✅

## 兼容性说明
- 当 `data.logical_tree` 不存在或不合法时：自动回退到经典树布局（classic）
- 用户可手动切到 Classic 模式，不影响现有树视图能力
