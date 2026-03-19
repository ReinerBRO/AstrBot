import asyncio
import os
import sys
import traceback
from pathlib import Path

import click
from filelock import FileLock, Timeout

from ..utils import check_persbot_root, check_dashboard, get_persbot_root


async def run_persbot(persbot_root: Path) -> None:
    """Run Persbot"""
    from persbot.core import LogBroker, LogManager, db_helper, logger
    from persbot.core.initial_loader import InitialLoader

    await check_dashboard(persbot_root / "data")

    log_broker = LogBroker()
    LogManager.set_queue_handler(logger, log_broker)
    db = db_helper

    core_lifecycle = InitialLoader(db, log_broker)

    await core_lifecycle.start()


@click.option("--reload", "-r", is_flag=True, help="Auto-reload plugins")
@click.option("--port", "-p", help="Persbot Dashboard port", required=False, type=str)
@click.command()
def run(reload: bool, port: str) -> None:
    """Run Persbot"""
    try:
        os.environ["PERSBOT_CLI"] = "1"
        persbot_root = get_persbot_root()

        if not check_persbot_root(persbot_root):
            raise click.ClickException(
                f"{persbot_root} is not a valid Persbot root directory. Use 'persbot init' to initialize",
            )

        os.environ["PERSBOT_ROOT"] = str(persbot_root)
        sys.path.insert(0, str(persbot_root))

        if port:
            os.environ["DASHBOARD_PORT"] = port

        if reload:
            click.echo("Plugin auto-reload enabled")
            os.environ["PERSBOT_RELOAD"] = "1"

        lock_file = persbot_root / "persbot.lock"
        lock = FileLock(lock_file, timeout=5)
        with lock.acquire():
            asyncio.run(run_persbot(persbot_root))
    except KeyboardInterrupt:
        click.echo("Persbot has been shut down.")
    except Timeout:
        raise click.ClickException(
            "Cannot acquire lock file. Please check if another instance is running"
        )
    except Exception as e:
        raise click.ClickException(f"Runtime error: {e}\n{traceback.format_exc()}")
