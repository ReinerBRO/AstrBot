import ctypes
import logging
import platform
import time
from ctypes.util import find_library
from typing import Callable

from watcher.event_source.models import ClickEvent

LOGGER = logging.getLogger(__name__)

try:
    from pynput import mouse as pynput_mouse
except Exception:
    pynput_mouse = None


def _button_name(value: object) -> str:
    text = str(value or "").lower()
    if "right" in text:
        return "right"
    if "middle" in text:
        return "middle"
    return "left"


def check_accessibility_permission() -> bool:
    if platform.system() != "Darwin":
        return True
    try:
        lib_path = find_library("ApplicationServices") or (
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        lib = ctypes.CDLL(lib_path)
        if hasattr(lib, "CGPreflightListenEventAccess"):
            lib.CGPreflightListenEventAccess.restype = ctypes.c_bool
            lib.CGPreflightListenEventAccess.argtypes = []
            return bool(lib.CGPreflightListenEventAccess())
        if hasattr(lib, "AXIsProcessTrusted"):
            lib.AXIsProcessTrusted.restype = ctypes.c_bool
            lib.AXIsProcessTrusted.argtypes = []
            return bool(lib.AXIsProcessTrusted())
    except Exception:
        return False
    return False


class ClickListener:
    def __init__(self, callback: Callable[[ClickEvent], None]):
        self._callback = callback
        self._listener = None
        self._running = False

    def start(self) -> bool:
        if self._running:
            return True
        if pynput_mouse is None:
            LOGGER.warning("pynput not installed; click listener disabled")
            return False
        if platform.system() == "Darwin" and not check_accessibility_permission():
            LOGGER.warning(
                "macOS accessibility/input-monitoring permission not granted"
            )
            return False

        def on_click(x, y, button, pressed):
            if not pressed:
                return
            event = ClickEvent(
                ts=time.time(),
                x=int(x),
                y=int(y),
                button=_button_name(button),
            )
            try:
                self._callback(event)
            except Exception:
                LOGGER.exception("click callback failed")

        try:
            self._listener = pynput_mouse.Listener(on_click=on_click)
            self._listener.start()
            self._running = True
            return True
        except Exception:
            LOGGER.exception("failed to start click listener")
            self._listener = None
            self._running = False
            return False

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        self._running = False
        if listener is None:
            return
        try:
            listener.stop()
            listener.join(timeout=1)
        except Exception:
            LOGGER.exception("failed to stop click listener")

    def is_running(self) -> bool:
        return self._running
