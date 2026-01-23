"""
Production server launcher from the repository root.

Adds the API package to sys.path, loads environment variables, and serves the
application via Waitress. This mirrors the previous api/run_server.py script so
existing deployment instructions continue to work.
"""
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.dont_write_bytecode = True





BASE_DIR = Path(__file__).resolve().parent
API_DIR = BASE_DIR / "api"
sys.path.insert(0, str(API_DIR))

load_dotenv()

from waitress import serve  # noqa: E402
from config.wsgi import application  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("=" * 70)
    logger.info("Starting Personal Assistant API with Waitress (Production Server)")
    logger.info("=" * 70)
    port_env = (
        os.getenv("PORT")
        or os.getenv("APP_PORT")
        or os.getenv("DEFAULT_PORT")
        or "8080"
    )
    try:
        port = int(port_env)
    except ValueError:
        logger.warning(
            "Invalid port value '%s' from environment. Falling back to 8080.", port_env
        )
        port = 8080
    logger.info("Server: http://0.0.0.0:%s", port)
    logger.info("API Docs: http://0.0.0.0:%s/api/docs/", port)
    logger.info(
        "Health Check: http://0.0.0.0:%s/api/personal_assistant/health", port
    )
    logger.info("=" * 70)
    logger.info("Worker Threads: 8")
    logger.info("Timeout: 640 seconds (for long-running analyses)")
    logger.info("=" * 70)
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 70)

    try:
        serve(
            application,
            host="0.0.0.0",
            port=port,
            threads=8,
            _quiet=False,
            _start=True,
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as exc:  # pragma: no cover - logging unexpected errors
        logger.error("Server error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
