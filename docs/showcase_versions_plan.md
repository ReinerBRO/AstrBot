# Persbot 五版本展示方案

## 方案原则

不再维护五份 `worktree`。现在统一采用：

- 一个最终版主仓库
- 五个前端启动入口
- 启动时通过 `VITE_PERSBOT_SHOWCASE_VERSION` 决定当前展示版本
- 通过前端隐藏菜单、路由、扩展页标签和首页入口来制造清晰的版本梯度

这样做的好处是：

- 不需要维护五份代码副本
- 不改后端主逻辑，风险更低
- 每个版本差异都能在界面上直接看出来
- 组会时只要换启动命令，不需要切分支或切目录

## 启动方式

在 `dashboard` 目录下使用：

```bash
pnpm dev:v1
pnpm dev:v2
pnpm dev:v3
pnpm dev:v4
pnpm dev:v5
```

如果本机没有全局 `pnpm`，可以改用：

```bash
npx --yes pnpm@10.32.1 dev:v1
npx --yes pnpm@10.32.1 dev:v2
npx --yes pnpm@10.32.1 dev:v3
npx --yes pnpm@10.32.1 dev:v4
npx --yes pnpm@10.32.1 dev:v5
```

## 五个版本的切分逻辑

| 版本 | 阶段进度 | 展示定位 | 本版开放模块 | 本版仍隐藏模块 |
| --- | --- | --- | --- | --- |
| V1 | 25% | Base Agent | 欢迎页、聊天、Provider、Config | 机器人、知识库、Persona、插件、Skills、MCP、会话管理、定时任务、多代理、Console、Trace |
| V2 | 43.75% | Connected Workspace | V1 全部 + 机器人接入 + Knowledge Base + Persona | 插件、Skills、MCP、会话管理、定时任务、多代理、Console、Trace |
| V3 | 62.5% | Plugin Ecosystem | V2 全部 + 已装插件 + 插件市场 + Skills | MCP、组件面板、会话管理、定时任务、多代理、Console、Trace |
| V4 | 81.25% | Operational Agent | V3 全部 + Conversation + Session Management + Cron + SubAgent + Dashboard | MCP、组件面板、Console、Trace |
| V5 | 100% | Full Persbot | V4 全部 + MCP + Components + Console + Trace | 无 |

## 六人方向映射

这部分按 `../daily` 里的组内材料统一下来，后面的五版汇报都沿用这一套职责主线：

| 成员 | 方向 | 在 daily 中出现的关键词 |
| --- | --- | --- |
| Yi Ding | Cognitive Engine | multi-stage CoT, hierarchical task trees, recursive backtracking |
| Jinchang Zhu | Agent Memory System | Graph Core, Episodic/Semantic/Profile/Pattern, Dual-Path Retrieval, Auto-Consolidation |
| Chenghao Wu | Semantic Recommendation | Graph-Enhanced Reranking, User Interest Profiles, proactive search |
| Xiaojian Nie | Visual Workflow | pixel-to-intent mapping, demonstration learning, DOM-based logic scripts |
| Ying Liu | Behavior Alignment | jailbreak-driven framework, boundary discovery, RLVR/GRPO |
| Yaxin Li | Security and Privacy Framework | zero-knowledge, sandboxing, local processing, differential privacy, secure TEE |

## 每一版必须满足的展示要求

每个版本都必须同时满足下面三条：

1. 屏幕上看得出来
   这一版必须有明显消失或明显新增的菜单、页面、按钮、标签。
2. 嘴上讲得出来
   这一版必须能用一句话说清楚相对上一版新增了什么。
3. 每个人都有话讲
   六个人都必须能明确说出自己这一版负责的具体模块、阶段目标和相对上一版新增的部分。

## 推荐的整体叙事线

- V1：我们先把最终系统裁成一个最小可演示的基础 Agent
- V2：在基础 Agent 上补齐接入、知识和人格
- V3：再开放插件生态，让系统可扩展
- V4：再开放运营和自动化，让系统可以跑起来
- V5：最后开放 MCP 和观测能力，形成完整系统

## 文档索引

- 总体讲解与启动说明：`docs/showcase_versions_plan.md`
- Demo 演示顺序：`docs/showcase_demo_playbook.md`
- 各版本具体内容：
  - `docs/showcase/v1-base-agent.md`
  - `docs/showcase/v2-connected-workspace.md`
  - `docs/showcase/v3-plugin-ecosystem.md`
  - `docs/showcase/v4-operational-agent.md`
  - `docs/showcase/v5-full-persbot.md`
