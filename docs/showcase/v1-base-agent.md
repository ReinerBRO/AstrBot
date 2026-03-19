# V1 Base Agent

## 启动入口

```bash
pnpm dev:v1
```

## 本版更新

- 进度定位：首版约占整体 25%
- 用最终版代码基座裁出最小可演示 Agent
- 只保留欢迎页、聊天、Provider、Config
- 全面隐藏机器人、知识库、Persona、插件、MCP 和运维能力

## Demo 上能直接看见的变化

- 左侧菜单明显变短
- 扩展页、机器人页、知识库页都看不到
- 欢迎页顶部会显示 `V1 Base Agent`

## 六人具体工作

1. Yi Ding（Cognitive Engine）：把系统先收敛成单 Agent 的基础认知闭环，只保留最小的对话、模型调用和配置链路，不在 V1 暴露 task tree、subagent 或复杂工具编排。
2. Jinchang Zhu（Agent Memory System）：先定义记忆系统的最小接入面，保留聊天历史与用户上下文的基础接口，但不在 V1 打开 Knowledge Base、Persona 或长期记忆展示页。
3. Chenghao Wu（Semantic Recommendation）：把推荐模块留在冷启动阶段，只保留后续会接入 user interest profile 的接口约束，不在 V1 提前暴露主动推荐能力，避免没有记忆输入时讲不圆。
4. Xiaojian Nie（Visual Workflow）：把视觉工作流和 GUI 执行能力整体收住，只保留最基础的平台/系统壳层，不在 V1 暴露 CV 识别、脚本生成或自动执行页面。
5. Ying Liu（Behavior Alignment）：用“先缩能力面”的方式完成第一阶段对齐收口，V1 故意不开放插件、多代理、定时任务等高风险能力，让基础 Agent 的行为边界足够清晰。
6. Yaxin Li（Security and Privacy Framework）：把 V1 定义成最低风险基线，只保留本地配置与基础调用链路，暂不开放插件、MCP、自动化与外部工具入口，先把攻击面压到最小。

## 组会直接可说

- 整组：`V1 的目标不是展示全功能，而是先把 Persbot 收缩成一个最小可用的 Personalized Agent。`
- Yi Ding：`我这一版先把认知引擎收敛成最小闭环，只保留基础对话和模型调用，不提前展示复杂规划。`
- Jinchang Zhu：`我这一版把记忆系统先做成接口预留状态，不急着展示长期记忆页面，先保证基础 Agent 说得通。`
- Chenghao Wu：`我这一版把推荐模块留在冷启动阶段，等 Persona 和 Knowledge Base 打开后再让推荐变得有依据。`
- Xiaojian Nie：`我这一版先不展示视觉工作流，避免在最初版本就把执行层放出来导致系统显得过重。`
- Ying Liu：`我这一版主要做的是能力面收口，让 V1 的行为边界清晰可控。`
- Yaxin Li：`我这一版把安全策略落在最小攻击面上，先不开放插件、MCP 和自动化接口。`
