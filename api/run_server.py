"""
Production-ready Waitress server launcher for Personal Assistant API
Waitress is Windows-compatible and production-tested
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Import after path setup
from waitress import serve
from api_config.wsgi import application

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("Starting Personal Assistant API with Waitress (Production Server)")
    logger.info("=" * 70)
    logger.info("Server: http://0.0.0.0:8000")
    logger.info("API Docs: http://0.0.0.0:8000/api/docs/")
    logger.info("ReDoc Docs: http://0.0.0.0:8000/api/redoc/")
    logger.info("Health Check: http://0.0.0.0:8000/api/personal_assistant/health")
    logger.info("=" * 70)
    logger.info("Worker Threads: 4")
    logger.info("Timeout: 640 seconds (for long-running analyses)")
    logger.info("=" * 70)
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 70)
    
    try:
        serve(
            application,
            host='0.0.0.0',
            port=8000,
            threads=4,  
            _quiet=False,
            _start=True
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
