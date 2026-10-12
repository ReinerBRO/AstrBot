# Persbot Showcase Startup Guide

## 10.14RBM：部署当前记忆展示版本

组会演示使用 `10.14RBM` 分支。仓库包含记忆模块、图谱界面、可初始化的会话与关联数据；不包含个人聊天数据库或 API Key。

### 安装和启动

```bash
git clone --branch 10.14RBM https://github.com/ReinerBRO/AstrBot.git persbot
cd persbot
uv sync
cd dashboard
pnpm install
pnpm build
cd ..
uv run main.py --webui-dir dashboard/dist
```

打开 `http://127.0.0.1:6185`，在「模型提供商」里配置自己的 ZZZ Key，API Base 为 `https://api.zhizengzeng.com/v1`，聊天模型选择并启用 `gpt-4o-mini`，设为当前默认聊天模型。网关也需要支持 `text-embedding-3-small`，用于现场问题的真实语义检索。

### 初始化演示记忆（服务运行后，在另一个终端执行一次）

```bash
curl --fail-with-body -X POST http://127.0.0.1:6185/api/memory/initialize-demo \
  -H 'Content-Type: application/json' \
  -d '{}'
```

成功返回 `status: ok`，安装 **5 段 Chat 会话、34 轮对话、39 条记忆**及已保存的关联；同时启用语义记忆。初始化使用当前仪表盘用户，无需复制原作者账号或数据库。重复执行不会重复插入，也不会删除已有聊天；若已有记忆使用不同编码器，先在记忆设置中重建索引。初始化只重算 embedding，不重新生成历史回复和归纳。

进入左侧「记忆展示」（`http://127.0.0.1:6185/#/memory`），选择「HeLa 激活对照」，保持每侧 **Top-4**，现场逐一输入：

1. 我是在几月几日向 Melanie 谈起自己给学生分享经历的？
2. 我第一次在哪里遇见那位影响我职业选择的人？

关键事实分别是 **2023 年 6 月 9 日**（谈起这件事的日期，不是学校活动日期）、**收养支持会议**。第一个问题使用真实语义排序和保存的关联；第二个沿用论文案例的明确预设检索分数。两侧均由当前 `gpt-4o-mini` 使用正常 Chat 人格提示词现场回答，没有写死回答或强制拒答/引用编号；模型表述和是否答出事实可能变化，正式展示前请在部署机器上预演。

Chat 与图谱共享这份记忆，新聊天会继续写入；对照页面只读，不会把测试问题写进记忆。为了保留初始化时的检索对照，先在「记忆展示」中演示这两个问题，再进行会写入新记忆的 Chat 演示。部署时保留 `data/`，不要在重启容器时丢弃该目录。

演示数据中的前三段会话摘自 [LoCoMo](https://github.com/snap-research/locomo) 的 `conv-26 / Caroline`，作者为 Adyasha Maharana、Dong-Ho Lee、Sergey Tulyakov、Mohit Bansal、Francesco Barbieri、Yuwei Fang，遵循 [CC BY-NC 4.0](https://github.com/snap-research/locomo/blob/main/LICENSE.txt)。本项目保留这些用户话语，配以此前 `gpt-4o-mini` 生成的回复、归纳及记忆关联；未打包 QA 标准答案或个人后续聊天。许可副本见 `persbot/core/memory/fixtures/LOCOMO_LICENSE.txt`。另两段为已有论文案例与手工背景记录。

---

这个仓库现在按“单一最终代码基座 + 5 个前端展示入口”来演示 5 个版本。

## 1. 安装依赖

后端：

```bash
uv sync
```

前端：

```bash
cd dashboard
pnpm install
```

如果没有全局 `pnpm`，可以改用：

```bash
npx --yes pnpm@10.32.1 install
```

## 2. 启动后端

在仓库根目录运行：

```bash
uv run main.py
```

默认后端地址：

- API: `http://localhost:6185`

## 3. 启动前端 5 个版本

在 `dashboard` 目录运行：

```bash
pnpm dev:v1
pnpm dev:v2
pnpm dev:v3
pnpm dev:v4
pnpm dev:v5
```

如果没有全局 `pnpm`，可以改用：

```bash
npx --yes pnpm@10.32.1 dev:v1
npx --yes pnpm@10.32.1 dev:v2
npx --yes pnpm@10.32.1 dev:v3
npx --yes pnpm@10.32.1 dev:v4
npx --yes pnpm@10.32.1 dev:v5
```

默认前端地址：

- WebUI: `http://localhost:3000`

## 4. 构建前端 5 个版本

在 `dashboard` 目录运行：

```bash
pnpm build:v1
pnpm build:v2
pnpm build:v3
pnpm build:v4
pnpm build:v5
```

如果没有全局 `pnpm`，可以改用：

```bash
npx --yes pnpm@10.32.1 build:v1
npx --yes pnpm@10.32.1 build:v2
npx --yes pnpm@10.32.1 build:v3
npx --yes pnpm@10.32.1 build:v4
npx --yes pnpm@10.32.1 build:v5
```

## 5. 五个版本对应关系

- `v1`: Base Agent
- `v2`: Connected Workspace
- `v3`: Plugin Ecosystem
- `v4`: Operational Agent
- `v5`: Full Persbot

## 6. 版本说明文档

版本总方案：

- `docs/showcase_versions_plan.md`
- `docs/showcase_demo_playbook.md`

逐版说明：

- `docs/showcase/v1-base-agent.md`
- `docs/showcase/v2-connected-workspace.md`
- `docs/showcase/v3-plugin-ecosystem.md`
- `docs/showcase/v4-operational-agent.md`
- `docs/showcase/v5-full-persbot.md`

## 7. 当前展示环境说明

- 5 个版本共用同一套后端与同一套最终代码
- 版本差异由前端启动入口控制
- 登录与注册流程已移除，打开 WebUI 直接进入系统

<a href="https://discord.gg/hAVk6tgV36"><img alt="Discord_community" src="https://img.shields.io/badge/Discord-Persbot-purple?style=for-the-badge&color=76bad9"></a>

## ❤️ Special Thanks

Special thanks to all Contributors and plugin developers for their contributions to Persbot ❤️

<a href="https://github.com/PersbotDevs/Persbot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=PersbotDevs/Persbot&max=200&columns=14" />
</a>

Additionally, the birth of this project would not have been possible without the help of the following open-source projects:

- [NapNeko/NapCatQQ](https://github.com/NapNeko/NapCatQQ) - The amazing cat framework

## ⭐ Star History

> [!TIP]
> If this project has helped you in your life or work, or if you're interested in its future development, please give the project a Star. It's the driving force behind maintaining this open-source project <3

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=persbotdevs/persbot&type=Date)](https://star-history.com/#persbotdevs/persbot&Date)

</div>

<div align="center">

_Companionship and capability should never be at odds. What we aim to create is a robot that can understand emotions, provide genuine companionship, and reliably accomplish tasks._

_私は、高性能ですから!_

<img src="https://files.persbot.app/watashiwa-koseino-desukara.gif" width="100"/>
</div>
