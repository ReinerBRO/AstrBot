# V4 Operational Agent

## 启动入口

```bash
pnpm dev:v4
```

## 本版更新

- 进度定位：累计约 81.25%
- 在 V3 基础上开放 Conversation、Session Management、Cron、SubAgent、Dashboard
- 系统从“可扩展”升级到“可运营、可调度、可编排”

## Demo 上能直接看见的变化

- 左侧更多菜单明显增加
- 能看到会话归档、会话管理、定时任务、多代理、运营看板
- 还看不到 `MCP`、`Components`、`Console`、`Trace`
- 欢迎页顶部显示 `V4 Operational Agent`

## 六人具体工作

1. Yi Ding（Cognitive Engine）：把认知引擎从单轮对话推进到多阶段任务树，V4 能讲清楚的点是 conversation、session、cron、subagent 这些入口开始服务更长链路的规划与编排。
2. Jinchang Zhu（Agent Memory System）：把 Conversation 和 Session Management 视为 episodic memory 的显式沉淀层，系统开始真正积累会话轨迹、运行日志和后续 consolidation 所需的数据。
3. Chenghao Wu（Semantic Recommendation）：把推荐从静态画像推进到动态反馈，V4 可以顺着 session、dashboard、cron 去讲“系统开始具备主动提醒和主动建议的基础运营能力”。
4. Xiaojian Nie（Visual Workflow）：把执行层和运营层接起来，视觉工作流在这一版虽然不单独开页面，但它的合理口径是“未来学到的流程可以被 cron 调度、被 subagent 调用、被会话链路复用”。
5. Ying Liu（Behavior Alignment）：把对齐重点放到长链路和主动行为上，尤其是定时任务、多代理协作和持续运行的场景，确保系统不是只有功能可见，而是行为也可控。
6. Yaxin Li（Security and Privacy Framework）：把安全重点切到运行期，围绕会话管理、调度、运营看板这些入口强调权限、审计和运行边界，不让系统因为开始“能运营”就失去可控性。

## 组会直接可说

- 整组：`V4 相比 V3，核心升级是 Persbot 不只是能扩展，而是开始能运营和调度。`
- Yi Ding：`我这一版把认知引擎推进到多阶段任务树，系统开始能支撑 session、cron 和 subagent 这种长链路规划。`
- Jinchang Zhu：`我这一版重点是把会话和运行轨迹沉淀成真正可积累的 episodic memory。`
- Chenghao Wu：`我这一版把推荐从静态画像推进到动态反馈，系统开始具备主动提醒和主动建议的运营基础。`
- Xiaojian Nie：`我这一版把执行层和调度层串起来，让未来的工作流能力能被定时任务和多代理复用。`
- Ying Liu：`我这一版主要盯长链路对齐问题，尤其是定时任务和多代理协作的行为边界。`
- Yaxin Li：`我这一版主要讲运行期安全，系统开始能运营以后，权限和审计边界就必须补上。`
