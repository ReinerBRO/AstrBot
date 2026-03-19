from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from app.main import main


if __name__ == "__main__":
    main()
