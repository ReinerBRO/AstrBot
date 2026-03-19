import platform
import subprocess
import time

from watcher.event_source.models import WindowInfo


class WindowResolver:
    @staticmethod
    def get_active_window(mask_title: bool = False) -> WindowInfo:
        ts = time.time()
        if platform.system() != "Darwin":
            return WindowInfo(
                app_name="Unknown",
                window_title="",
                bundle_id=None,
                timestamp=ts,
            )
        app_name, window_title, bundle_id = WindowResolver._get_active_window_macos()
        if mask_title and window_title:
            window_title = WindowResolver._mask_title(window_title)
        return WindowInfo(
            app_name=app_name or "Unknown",
            window_title=window_title,
            bundle_id=bundle_id,
            timestamp=ts,
        )

    @staticmethod
    def _get_active_window_macos() -> tuple[str, str, str | None]:
        script = """
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            try
                set winTitle to name of front window of frontApp
            on error
                set winTitle to ""
            end try
        end tell
        return appName & tab & winTitle
        """
        bundle_script = """
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            return bundle identifier of frontApp
        end tell
        """
        app_name = "Unknown"
        window_title = ""
        bundle_id = None
        try:
            proc = subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            raw = (proc.stdout or "").strip()
            if raw:
                parts = [part.strip() for part in raw.split("\t")]
                app_name = (parts[0] if parts else "") or "Unknown"
                if len(parts) > 1:
                    window_title = parts[1]
                if len(parts) > 2 and parts[2]:
                    bundle_id = parts[2]
        except Exception:
            pass
        if bundle_id is None:
            try:
                proc = subprocess.run(
                    ["osascript", "-e", bundle_script],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                raw = (proc.stdout or "").strip()
                bundle_id = raw or None
            except Exception:
                bundle_id = None
        return app_name, window_title, bundle_id

    @staticmethod
    def _mask_title(title: str) -> str:
        text = (title or "").strip()
        if not text:
            return ""
        if len(text) <= 6:
            return "***"
        return f"{text[:3]}***{text[-2:]}"
