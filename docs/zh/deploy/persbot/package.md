# 包管理器部署（uv）

使用 `uv` 可以快速安装并启动 Persbot。

## 前置条件

如果尚未安装 `uv`，请先按照官方文档安装：<https://docs.astral.sh/uv/>

`uv` 支持 Linux、Windows、macOS。

## 安装并启动

```bash
uv tool install persbot
persbot init # 只需要在第一次部署时执行，后续启动不需要执行
persbot run
```
