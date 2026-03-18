# Deploy Persbot with Persbot Launcher

## Recommended Method 1: Persbot One-Click Launcher

Persbot One-Click Launcher supports Windows, macOS, and Linux.

0. Open [PersbotDevs/persbot-launcher](https://github.com/PersbotDevs/persbot-launcher)
1. **Optional but recommended**: give this project a [**Star ⭐**](https://github.com/PersbotDevs/persbot-launcher). Your support helps maintainers keep improving it.
2. Find **Releases** on the right, open the latest release, then download the installer for your system from **Assets**.

For example:

- Windows x86 users: `Persbot.Launcher_0.2.1_x64-setup.exe`
- Windows on Arm users: `Persbot.Launcher_0.2.1_arm64-setup.exe`
- macOS Apple Silicon users: `Persbot.Launcher_0.2.1_aarch64.dmg`

For macOS users, if you see "damaged and can't be opened", it is caused by macOS security restrictions on unsigned apps. Fix it with:

1. Open Terminal.
2. Run:
   `xattr -dr com.apple.quarantine /Applications/Persbot\ Launcher.app`
3. Reopen Persbot Launcher.

## Method 2: Legacy Windows Installer

We still recommend the One-Click Launcher above because it is simpler, more automated, and better for most users.

The legacy installer is a `PowerShell` script, very small (<20KB). It requires `PowerShell` (usually built in on `Windows 10` and newer).

> [!WARNING]
> `Python 3.10` or later must be installed, and environment variables must be configured.

> [!TIP]
> If deployment fails, try Docker deployment or manual deployment instead.

## Download the Legacy Installer

Open <https://github.com/PersbotDevs/PersbotLauncher/releases/latest>

Download `Source code (zip)` and extract it.

## Run the Legacy Installer

> The video may be outdated. Follow the steps here.

After extraction, open the folder.

Type `PowerShell` in the address bar and press Enter:

![image](https://files.persbot.app/docs/source/images/windows/image-4.png)

Drag `launcher_persbot_en.bat` into the PowerShell window and press Enter.

> [!WARNING]
> - The script is safe. If you see `Windows protected your PC`, click `More info` and then `Run anyway`.
> - By default, it uses `python`. If you want to specify another interpreter path/command, edit `launcher_persbot_en.bat`, find `set PYTHON_CMD=python`, and replace `python` with your own command/path.

If Python is not detected, the script exits with a prompt.

The script checks whether an `Persbot` folder exists. If not, it downloads the latest Persbot source from [GitHub](https://github.com/PersbotDevs/Persbot/releases/latest), installs dependencies, and runs it automatically.

## Done

If everything works, you will see Persbot logs.

Without errors, you should see a log like `🌈 Management panel started, accessible at` with several URLs. Open one URL to access Persbot WebUI.

> [!TIP]
> Default username and password: `persbot` / `persbot`.
>
> If WebUI returns 404:
> Download `dist.zip` from [release](https://github.com/PersbotDevs/Persbot/releases), extract it into `Persbot/data`, then restart the computer if needed.

Then deploy at least one messaging platform adapter to start using Persbot in IM apps.

## Error: Python is not installed

If you still get this error after installing Python and restarting, your PATH is likely incorrect.

**Method 1**

Search for Python in Windows and open its file location:

![image](https://files.persbot.app/docs/source/images/windows/image.png)

Right-click the shortcut below and open file location:

![alt text](https://files.persbot.app/docs/source/images/windows/image-1.png)

Copy the file path:

![image](https://files.persbot.app/docs/source/images/windows/image-2.png)

Edit `launcher_persbot_en.bat` in Notepad, find `set PYTHON_CMD=python`, and replace `python` with your interpreter command/path. Keep quotes if your path contains spaces.

**Method 2**

Reinstall Python, check `Add Python to PATH` during installation, then restart your computer.
