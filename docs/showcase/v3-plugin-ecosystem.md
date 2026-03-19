# V3 Plugin Ecosystem

## 启动入口

```bash
pnpm dev:v3
```

## 本版更新

- 进度定位：累计约 62.5%
- 在 V2 基础上开放 Extension 模块
- 开放 Installed Plugins、Plugin Market、Skills
- 系统从“固定功能”升级到“可扩展生态”

## Demo 上能直接看见的变化

- 左侧多出 `Extension`
- 打开扩展页后能看到 `Installed / Market / Skills`
- 还看不到 `MCP` 和 `Components`
- 欢迎页顶部显示 `V3 Plugin Ecosystem`

## 六人具体工作

1. Yi Ding（Cognitive Engine）：把认知引擎从“理解用户”推进到“理解可调用能力”，开始围绕 Skills、插件和扩展能力建立 tool-aware 的任务分解思路。
2. Jinchang Zhu（Agent Memory System）：给记忆系统补上“工具偏好”和“能力使用轨迹”的存储视角，让系统以后不只是记住用户说过什么，也能记住用户常用哪类插件和技能。
3. Chenghao Wu（Semantic Recommendation）：把自己的 Graph-Enhanced Reranking 方向落到插件生态里，V3 最自然的讲法就是“为什么这个用户应该优先看到某些插件、技能和市场结果”。
4. Xiaojian Nie（Visual Workflow）：把可重复执行的动作抽象成 Skills/插件叙事，让后续视觉示教学出来的流程不只是一次性脚本，而是能沉淀成复用能力单元。
5. Ying Liu（Behavior Alignment）：在开放插件生态的同时定义扩展层的行为边界，先开放插件和 Skills，但继续压住 MCP 和更强外部工具能力，避免系统一下子跳到失控接口面。
6. Yaxin Li（Security and Privacy Framework）：把安全重点转到扩展沙箱上，V3 可以讲“系统开始可扩展了，但外部能力还停留在受控插件层，没有直接开放更深的工具链路”。

## 组会直接可说

- 整组：`V3 相比 V2，核心升级是 Persbot 从固定系统变成了可扩展系统。`
- Yi Ding：`我这一版开始让认知引擎面向工具能力做规划，系统不再只是理解用户，也开始理解“自己能做什么”。`
- Jinchang Zhu：`我这一版把记忆视角从用户内容扩展到工具偏好，为个性化插件使用做准备。`
- Chenghao Wu：`我这一版把推荐方向落到插件生态里，重点是插件市场和 Skills 的个性化排序逻辑。`
- Xiaojian Nie：`我这一版把未来的工作流能力先包装成 Skills 叙事，让执行层开始具备可复用形态。`
- Ying Liu：`我这一版的重点是扩展层边界，只开插件和 Skills，不急着开 MCP。`
- Yaxin Li：`我这一版主要讲扩展沙箱，系统开始可扩展，但还没有直接放开更深的外部工具接口。`
