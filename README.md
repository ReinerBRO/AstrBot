# Persbot Showcase Startup Guide

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
