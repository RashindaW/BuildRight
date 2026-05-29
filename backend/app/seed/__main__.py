from app.core.logging import setup_logging
from app.seed.seed import run

if __name__ == "__main__":
    setup_logging()
    run()
