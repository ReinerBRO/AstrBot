# V5 Full Persbot

## 启动入口

```bash
pnpm dev:v5
```

## 本版更新

- 进度定位：累计 100%
- 在 V4 基础上开放 `MCP`、`Components`、`Console`、`Trace`
- 打开最终完整菜单
- 从“可运营”升级到“完整 Persbot”

## Demo 上能直接看见的变化

- Extension 页新增 `MCP` 和 `Components`
- 左侧菜单新增 `Console` 和 `Trace`
- 整个系统不再有前端裁剪
- 欢迎页顶部显示 `V5 Full Persbot`

## 六人具体工作

1. Yi Ding（Cognitive Engine）：把认知引擎推进到完整态，V5 的核心口径是系统已经能面向 MCP、Components 和更复杂的外部能力做完整编排，真正接近你们 proposal 里的 agentic core。
2. Jinchang Zhu（Agent Memory System）：把记忆系统讲成真正的 Graph Core 闭环，前面几版累积下来的会话、画像、知识、工具偏好和执行轨迹，到 V5 才能自然收口为长期个性化记忆。
3. Chenghao Wu（Semantic Recommendation）：把推荐模块从“会推荐内容”推进到“会跨工具、跨记忆、跨组件做主动建议”，这时 Graph-Enhanced Reranking 的讲法最完整，因为输入面终于齐了。
4. Xiaojian Nie（Visual Workflow）：把视觉工作流和最终工具层接上，V5 最好讲的点是 GUI 执行不再只是孤立脚本，而是可以和 MCP、Components、技能体系放在同一个执行生态里。
5. Ying Liu（Behavior Alignment）：把 Console 和 Trace 作为对齐可观测面讲出来，系统现在不仅有能力，还能追踪失败路径、分析边界案例、为后续 jailbreak-driven alignment 提供反馈信号。
6. Yaxin Li（Security and Privacy Framework）：把最终版的安全叙事完整闭环，MCP、外部工具、运行轨迹、长期记忆都已经开放，所以这时要强调 zero-knowledge、sandbox、local processing、differential privacy 和 secure TEE。

## 组会直接可说

- 整组：`V5 相比 V4，核心升级是外部工具接入和系统可观测能力全部补齐，形成完整 Persbot。`
- Yi Ding：`我这一版把认知引擎推进到完整编排态，系统已经能围绕 MCP 和组件做真正的 agentic orchestration。`
- Jinchang Zhu：`我这一版把记忆系统收口成真正的 Graph Core，前面各版积累的用户信息和行为轨迹在这里形成长期个性化闭环。`
- Chenghao Wu：`我这一版的重点是跨工具和跨记忆的主动推荐，这时推荐系统终于有了完整输入面。`
- Xiaojian Nie：`我这一版把 GUI 工作流和最终工具层接上，让执行能力不再只是孤立脚本。`
- Ying Liu：`我这一版主要讲 Trace 和 Console 带来的对齐可观测性，系统不仅能做事，也能回看自己怎么做的。`
- Yaxin Li：`我这一版把最终版安全闭环讲完整，尤其是 MCP 打开后为什么还可以保证隐私和沙箱边界。`
