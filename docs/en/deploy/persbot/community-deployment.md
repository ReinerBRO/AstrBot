# Community-Provided Deployment Methods

> [!WARNING]
> Persbot official does not guarantee the security and stability of these deployment methods.

## Linux One-Click Deployment Script

Use `curl` to download the script and execute it using `bash`:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/zhende1113/Antlia/refs/heads/main/Script/Persbot/Antlia.sh)
```

If your system does not have `curl`, you can use `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/zhende1113/Antlia/refs/heads/main/Script/Persbot/Antlia.sh | bash
```

Repository Address: [zhende1113/Antlia](https://github.com/zhende1113/Antlia/)

## Linux One-Click Deployment Script (Based on Docker)

Supports Persbot / NapCat.

> [!TIP]
> Use `sudo` for elevated permissions if you have insufficient privileges.

### Using `curl`

```bash
curl -sSL https://raw.githubusercontent.com/railgun19457/PersbotScript/main/PersbotScript.sh -o PersbotScript.sh
chmod +x PersbotScript.sh
sudo ./PersbotScript.sh
```

### Using `wget`

```bash
wget -qO PersbotScript.sh https://raw.githubusercontent.com/railgun19457/PersbotScript/main/PersbotScript.sh
chmod +x PersbotScript.sh
sudo ./PersbotScript.sh
```

> [!note]
> `sudo ./PersbotScript.sh --no-color (Optional: disable color output)`

__Repository Address: [railgun19457/PersbotScript](https://github.com/railgun19457/PersbotScript)__

## Persbot Android Deployment

Refer to [zz6zz666/Persbot-Android-App](https://github.com/zz6zz666/Persbot-Android-App)