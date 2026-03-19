import asyncio
import os
import socket
import subprocess
import sys
import traceback
from pathlib import Path

import aiohttp

from persbot.core import logger
from persbot.core.utils.persbot_path import get_persbot_path, get_persbot_temp_path

from .route import Response, Route, RouteContext


class WatcherRoute(Route):
    WATCHER_HOST = "127.0.0.1"
    PREFERRED_PORT = 8001
    PORT_CANDIDATES = range(8001, 8011)
    READY_TIMEOUT_SECONDS = 90

    def __init__(self, context: RouteContext) -> None:
        super().__init__(context)
        self.routes = {
            "/watcher/status": ("GET", self.get_status),
            "/watcher/ensure": ("POST", self.ensure_watcher),
        }
        self._launch_lock = asyncio.Lock()
        self._watcher_process: subprocess.Popen | None = None
        self._active_port: int | None = None
        self.register_routes()

    @property
    def watcher_root(self) -> Path:
        return Path(get_persbot_path()) / "watcher"

    @property
    def watcher_requirements(self) -> Path:
        return self.watcher_root / "requirements.txt"

    @property
    def watcher_venv_dir(self) -> Path:
        return self.watcher_root / ".venv"

    @property
    def watcher_log_dir(self) -> Path:
        path = Path(get_persbot_temp_path()) / "watcher"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def watcher_log_file(self) -> Path:
        return self.watcher_log_dir / "watcher.log"

    @property
    def watcher_install_log_file(self) -> Path:
        return self.watcher_log_dir / "watcher-install.log"

    def _venv_python(self) -> Path:
        scripts_dir = "Scripts" if os.name == "nt" else "bin"
        python_name = "python.exe" if os.name == "nt" else "python"
        return self.watcher_venv_dir / scripts_dir / python_name

    def _build_base_url(self, port: int) -> str:
        return f"http://{self.WATCHER_HOST}:{port}"

    def _is_port_open(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex((self.WATCHER_HOST, port)) == 0

    async def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path,
        log_file: Path,
        timeout_seconds: int = 600,
    ) -> None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("ab") as handle:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(cwd),
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
            try:
                return_code = await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout_seconds,
                )
            except TimeoutError as exc:
                process.kill()
                await process.wait()
                raise RuntimeError(f"Command timed out: {' '.join(command)}") from exc

        if return_code != 0:
            raise RuntimeError(
                f"Command failed with exit code {return_code}: {' '.join(command)}"
            )

    async def _watcher_dependencies_ready(self) -> bool:
        python_path = self._venv_python()
        if not python_path.exists():
            return False

        process = await asyncio.create_subprocess_exec(
            str(python_path),
            "-c",
            "import dotenv, flask, mss, PIL, pynput, requests",
            cwd=str(self.watcher_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return await process.wait() == 0

    async def _ensure_watcher_environment(self) -> None:
        if not self.watcher_root.exists():
            raise FileNotFoundError(f"Watcher project not found: {self.watcher_root}")
        if not self.watcher_requirements.exists():
            raise FileNotFoundError(
                f"Watcher requirements file not found: {self.watcher_requirements}"
            )

        if not self._venv_python().exists():
            await self._run_command(
                [sys.executable, "-m", "venv", str(self.watcher_venv_dir)],
                cwd=self.watcher_root,
                log_file=self.watcher_install_log_file,
            )

        if await self._watcher_dependencies_ready():
            return

        python_path = self._venv_python()
        await self._run_command(
            [str(python_path), "-m", "pip", "install", "-U", "pip"],
            cwd=self.watcher_root,
            log_file=self.watcher_install_log_file,
        )
        await self._run_command(
            [
                str(python_path),
                "-m",
                "pip",
                "install",
                "-r",
                str(self.watcher_requirements),
            ],
            cwd=self.watcher_root,
            log_file=self.watcher_install_log_file,
        )

    async def _probe_watcher(self, port: int) -> dict | None:
        status_url = f"{self._build_base_url(port)}/api/status"
        timeout = aiohttp.ClientTimeout(total=2)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(status_url) as response:
                    if response.status != 200:
                        return None
                    payload = await response.json()
                    if payload.get("ok") is not True:
                        return None
        except Exception:
            return None

        self._active_port = port
        return {
            "running": True,
            "url": self._build_base_url(port),
            "port": port,
            "status": payload.get("data", {}),
        }

    async def _find_running_watcher(self) -> dict | None:
        ports: list[int] = []
        if self._active_port:
            ports.append(self._active_port)
        ports.extend(port for port in self.PORT_CANDIDATES if port not in ports)

        for port in ports:
            data = await self._probe_watcher(port)
            if data:
                return data
        return None

    def _pick_launch_port(self) -> int:
        for port in self.PORT_CANDIDATES:
            if not self._is_port_open(port):
                return port
        raise RuntimeError("No available port found for Watcher between 8001 and 8010")

    def _start_watcher_process(self, port: int) -> subprocess.Popen:
        env = os.environ.copy()
        env["WATCHER_HOST"] = self.WATCHER_HOST
        env["WATCHER_PORT"] = str(port)
        log_handle = self.watcher_log_file.open("ab")
        process = subprocess.Popen(  # noqa: S603
            [str(self._venv_python()), "run.py"],
            cwd=str(self.watcher_root),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            close_fds=True,
        )
        log_handle.close()
        self._watcher_process = process
        self._active_port = port
        return process

    def _tail_log(self, log_file: Path, max_lines: int = 20) -> str:
        if not log_file.exists():
            return ""
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return ""
        tail = "\n".join(lines[-max_lines:])
        return tail.strip()

    async def _wait_until_ready(
        self,
        port: int,
        process: subprocess.Popen | None,
    ) -> dict:
        deadline = asyncio.get_running_loop().time() + self.READY_TIMEOUT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            running = await self._probe_watcher(port)
            if running:
                return running
            if process and process.poll() is not None:
                break
            await asyncio.sleep(1)

        log_tail = self._tail_log(self.watcher_log_file)
        if log_tail:
            raise RuntimeError(f"Watcher failed to become ready.\n{log_tail}")
        raise RuntimeError("Watcher failed to become ready.")

    async def get_status(self):
        try:
            data = await self._find_running_watcher()
            if data:
                return Response().ok(data).__dict__
            return (
                Response()
                .ok(
                    {
                        "running": False,
                        "url": None,
                        "port": None,
                        "status": {},
                    }
                )
                .__dict__
            )
        except Exception as exc:
            logger.error(traceback.format_exc())
            return Response().error(f"Failed to inspect Watcher: {exc!s}").__dict__

    async def ensure_watcher(self):
        async with self._launch_lock:
            try:
                running = await self._find_running_watcher()
                if running:
                    return Response().ok(running).__dict__

                await self._ensure_watcher_environment()

                running = await self._find_running_watcher()
                if running:
                    return Response().ok(running).__dict__

                port = self._pick_launch_port()
                process = self._start_watcher_process(port)
                data = await self._wait_until_ready(port, process)
                return Response().ok(data).__dict__
            except Exception as exc:
                logger.error(traceback.format_exc())
                install_log_tail = self._tail_log(self.watcher_install_log_file)
                if install_log_tail:
                    message = f"{exc!s}\n{install_log_tail}"
                else:
                    message = f"{exc!s}"
                return Response().error(message).__dict__
