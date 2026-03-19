import os
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

try:
    from app.web import create_app
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from app.web import create_app


def main():
    app = create_app()
    host = os.environ.get("WATCHER_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("WATCHER_PORT", "8001").strip() or "8001")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
