"""FastAPI HTTP server with rate limiting and validation."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from agent import CodeLocatorAgent
from metadata import CodeExplanation
from utils import validate_query

load_dotenv()
logger = logging.getLogger(__name__)

limiter = Limiter(
    key_func=get_remote_address, strategy="fixed-window", storage_uri="memory://"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle and resources."""
    logger.info("Initializing CodeLocatorAgent...")
    app.state.agent_instance = CodeLocatorAgent()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


async def get_agent(request: Request) -> CodeLocatorAgent:
    """Dependency injection for agent instance."""
    return request.app.state.agent_instance


app = FastAPI(
    title="Code Locator Agent API",
    description="Query httpx codebase with AI agent.",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded from {get_remote_address(request)}")
    return JSONResponse(
        status_code=429, content={"error": f"Rate limit exceeded: {exc.detail}"}
    )


@app.post("/query", response_model=CodeExplanation)
@limiter.limit("10/minute")
async def query_endpoint(
    request: Request,
    agent: CodeLocatorAgent = Depends(get_agent),
) -> CodeExplanation:
    """Process code explanation query.

    Args:
        request: HTTP request object
        agent: Injected agent instance

    Returns:
        CodeExplanation with symbols, locations, and explanation
    """
    body = await request.body()
    text_query = body.decode("utf-8").strip()

    if not text_query:
        raise HTTPException(400, "Empty query")

    validated_query = validate_query(text_query)
    response = await agent.run_query(validated_query)

    return response
