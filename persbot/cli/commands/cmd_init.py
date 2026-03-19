import asyncio
from pathlib import Path

import click
from filelock import FileLock, Timeout

from ..utils import check_dashboard, get_persbot_root


async def initialize_persbot(persbot_root: Path) -> None:
    """Execute Persbot initialization logic"""
    dot_persbot = persbot_root / ".persbot"

    if not dot_persbot.exists():
        if click.confirm(
            f"Install Persbot to this directory? {persbot_root}",
            default=True,
            abort=True,
        ):
            dot_persbot.touch()
            click.echo(f"Created {dot_persbot}")

    paths = {
        "data": persbot_root / "data",
        "config": persbot_root / "data" / "config",
        "plugins": persbot_root / "data" / "plugins",
        "temp": persbot_root / "data" / "temp",
    }

    for name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        click.echo(f"{'Created' if not path.exists() else 'Directory exists'}: {path}")

    await check_dashboard(persbot_root / "data")


@click.command()
def init() -> None:
    """Initialize Persbot"""
    click.echo("Initializing Persbot...")
    persbot_root = get_persbot_root()
    lock_file = persbot_root / "persbot.lock"
    lock = FileLock(lock_file, timeout=5)

    try:
        with lock.acquire():
            asyncio.run(initialize_persbot(persbot_root))
            click.echo("Done! You can now run 'persbot run' to start Persbot")
    except Timeout:
        raise click.ClickException(
            "Cannot acquire lock file. Please check if another instance is running"
        )

    except Exception as e:
        raise click.ClickException(f"Initialization failed: {e!s}")
