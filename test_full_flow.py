#!/usr/bin/env python
"""Integration test for lookup builder and MCP tool.

Tests the core functionality without starting HTTP/MCP servers:
- Environment configuration
- Symbol indexing (AST parsing)
- Symbol lookup queries
- MCP tool execution
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from lookup import LookupBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()


def check_environment() -> bool:
    """Verify required environment variables are set.

    Returns:
        True if all required vars present, False otherwise
    """
    logger.info("=" * 60)
    logger.info("ENVIRONMENT CHECK")
    logger.info("=" * 60)

    openai_key = os.getenv("OPENAI_API_KEY")
    mcp_url = os.getenv("MCP_SERVER_URL")
    httpx_dir = os.getenv("HTTPX_SOURCE_DIR", "./httpx/httpx")

    logger.info(f"OPENAI_API_KEY: {'✓ Set' if openai_key else '✗ NOT SET'}")
    logger.info(f"MCP_SERVER_URL: {mcp_url or '✗ NOT SET'}")
    logger.info(f"HTTPX_SOURCE_DIR: {httpx_dir}")

    # Check if httpx directory exists
    httpx_path = Path(httpx_dir)
    if httpx_path.exists():
        logger.info(f"✓ httpx directory found at {httpx_dir}")
    else:
        logger.error(f"✗ httpx directory not found at {httpx_dir}")
        logger.error("  Clone it: git clone https://github.com/encode/httpx.git")
        return False

    return True


def test_lookup_builder() -> LookupBuilder | None:
    """Test LookupBuilder initialization and symbol indexing.

    Returns:
        LookupBuilder instance if successful, None otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("TESTING LOOKUP BUILDER")
    logger.info("=" * 60)

    try:
        builder = LookupBuilder()
        builder.build()
        logger.info(f"✓ Lookup table built: {len(builder.lookup_table)} symbols")
        return builder
    except Exception as e:
        logger.error(f"✗ Failed to build lookup table: {e}")
        return None


def test_symbol_queries(builder: LookupBuilder) -> None:
    """Test symbol lookup queries.

    Args:
        builder: Initialized LookupBuilder instance
    """
    logger.info("")
    logger.info("TESTING SYMBOL QUERIES")
    logger.info("-" * 60)

    test_queries = [
        "Client.get",
        "AsyncClient.get",
        "AsyncHTTPTransport.handle_async_request",
    ]

    for query in test_queries:
        results = builder.query_symbols([query])
        if results:
            logger.info(f"✓ {query}: Found {len(results)} result(s)")
            for result in results:
                filename = Path(result.file_path).name
                logger.info(f"    {filename}:{result.start_line}-{result.end_line}")
        else:
            logger.warning(f"✗ {query}: NOT FOUND")


async def test_mcp_tool() -> bool:
    """Test MCP tool execution directly.

    Returns:
        True if test passed, False otherwise
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("TESTING MCP TOOL")
    logger.info("=" * 60)

    try:
        from mcp_server import get_source_code

        result = await get_source_code(["Client.get"])

        if not isinstance(result, dict):
            logger.error(f"✗ Unexpected result type: {type(result)}")
            return False

        matches = result.get("matches", [])
        error = result.get("error")

        if error:
            logger.error(f"✗ Tool returned error: {error}")
            return False

        logger.info("✓ MCP tool executed successfully")
        logger.info(f"  Matches found: {len(matches)}")

        if matches:
            first_match = matches[0]
            logger.info(f"  Symbol: {first_match['metadata']['name']}")
            logger.info(f"  Code length: {len(first_match.get('code', ''))} chars")

        return True

    except Exception as e:
        logger.exception(f"✗ MCP tool test failed: {e}")
        return False


def main() -> None:
    """Run all integration tests."""
    logger.info("Starting integration tests...")
    logger.info("")

    # Environment check
    if not check_environment():
        logger.error("Environment check failed. Exiting.")
        return

    # Lookup builder test
    builder = test_lookup_builder()
    if not builder:
        logger.error("Lookup builder test failed. Exiting.")
        return

    # Symbol query tests
    test_symbol_queries(builder)

    # MCP tool test
    mcp_success = asyncio.run(test_mcp_tool())

    # Summary
    logger.info("")
    logger.info("=" * 60)
    if mcp_success:
        logger.info("✓ ALL TESTS PASSED")
        logger.info("")
        logger.info("To test the full application:")
        logger.info("  1. Start server: python main.py")
        logger.info("  2. Query API:")
        logger.info("     curl -X POST http://localhost:8001/query \\")
        logger.info("          -d 'Explain Client.get'")
    else:
        logger.warning("⚠ Some tests failed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
