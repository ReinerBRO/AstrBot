# 社区提供的部署方式

> [!WARNING]
> Persbot 官方不保证这些部署方式的安全性和稳定性。

## Linux 一键部署脚本

使用 `curl` 去下载脚本并且使用 `bash` 执行脚本：

```bash
bash <(curl -sSL https://raw.githubusercontent.com/zhende1113/Antlia/refs/heads/main/Script/Persbot/Antlia.sh)
```

如果你的系统没有 `curl`，你可以使用 `wget`：

```bash
wget -qO- https://raw.githubusercontent.com/zhende1113/Antlia/refs/heads/main/Script/Persbot/Antlia.sh | bash
```

仓库地址：[zhende1113/Antlia](https://github.com/zhende1113/Antlia/)

## Linux 一键部署脚本（基于Docker）

支持 Persbot / NapCat

> [!TIP]
> 权限不足时请使用 `sudo` 提权

### 使用 `curl`

```bash
curl -sSL https://raw.githubusercontent.com/railgun19457/PersbotScript/main/PersbotScript.sh -o PersbotScript.sh
chmod +x PersbotScript.sh
sudo ./PersbotScript.sh
```

### 使用 `wget`

```bash
wget -qO PersbotScript.sh https://raw.githubusercontent.com/railgun19457/PersbotScript/main/PersbotScript.sh
chmod +x PersbotScript.sh
sudo ./PersbotScript.sh
```

> [!note]
> `sudo ./PersbotScript.sh --no-color (可选禁用彩色输出)`

__仓库地址：[railgun19457/PersbotScript](https://github.com/railgun19457/PersbotScript)__

## Persbot Android 部署

参考 [zz6zz666/Persbot-Android-App](https://github.com/zz6zz666/Persbot-Android-App)
