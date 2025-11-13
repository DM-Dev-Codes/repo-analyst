"""Main entry point for the application."""

import logging
from logging.handlers import RotatingFileHandler

import uvicorn
from dotenv import load_dotenv

from http_server import app
from mcp_server import mcp_app

load_dotenv()

# Configure logging with rotation
handlers = [
    logging.StreamHandler(),  # Console output
    RotatingFileHandler(
        "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    ),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)

# Reduce verbosity of noisy loggers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp.client.sse").setLevel(logging.WARNING)
logging.getLogger("mcp.server.sse").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Mount MCP server as sub-application
app.mount("/mcp", mcp_app)
logger.info("Mounted MCP server at /mcp")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Code Locator Agent API")
    logger.info("Main API: http://0.0.0.0:8001/query (POST)")
    logger.info("MCP SSE:  http://0.0.0.0:8001/mcp/sse")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )