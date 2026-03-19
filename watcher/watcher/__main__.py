from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from watcher.config import load_config
from watcher.runner import Watcher


def main():
    config = load_config()
    watcher = Watcher(config)
    watcher.run_forever()


if __name__ == "__main__":
    main()
