"""MCP server providing code lookup tools."""

import asyncio
import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from lookup import LookupBuilder
from metadata import SymbolLookupResult, SymbolMatch

load_dotenv()

logger = logging.getLogger(__name__)

mcp = FastMCP("code_explainer")

# Initialize lookup table at module load
logger.info("Initializing LookupBuilder...")
builder = LookupBuilder(os.getenv("HTTPX_SOURCE_DIR"))
logger.info("Building lookup table...")
builder.build()
logger.info(f"Lookup table ready with {len(builder.lookup_table)} entries")


@mcp.tool()
async def get_source_code(symbols: list[str]) -> SymbolLookupResult:
    """Look up source code for given symbols.

    Args:
        symbols: Symbol names (e.g., ["Client", "Client.get"])

    Returns:
        SymbolLookupResult with matches and code
    """
    logger.info(f"Tool called with symbols: {symbols}")

    try:
        metadata_results = await asyncio.to_thread(builder.query_symbols, symbols)
        logger.debug(f"Found {len(metadata_results)} metadata results")

        if not metadata_results:
            error_msg = f"No code found for symbols: {', '.join(symbols)}"
            logger.warning(error_msg)
            return SymbolLookupResult(matches=[], error=error_msg).model_dump()

        all_matches: list[SymbolMatch] = []
        for metadata in metadata_results:
            logger.debug(f"Processing {metadata.name} from {metadata.file_path}")

            try:
                code_chunk = await asyncio.to_thread(builder.get_code_chunk, metadata)

                if not code_chunk:
                    logger.warning(f"Empty code chunk for {metadata.name}")

            except FileNotFoundError as e:
                logger.error(f"File not found: {e}")
                code_chunk = f"# ERROR: {e}"
            except Exception as chunk_err:
                logger.exception(f"Failed to get code chunk: {chunk_err}")
                code_chunk = f"# ERROR: {chunk_err}"

            citation = f"{metadata.file_path}:{metadata.start_line}-{metadata.end_line}"

            try:
                match = SymbolMatch(
                    metadata=metadata, code=code_chunk, citation=citation
                )
                all_matches.append(match)
            except Exception as match_err:
                logger.exception(f"Failed to create SymbolMatch: {match_err}")

        logger.info(f"Returning {len(all_matches)} matches for {len(symbols)} symbols")
        result = SymbolLookupResult(matches=all_matches, error=None)
        return result.model_dump()

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return SymbolLookupResult(matches=[], error=str(e)).model_dump()


# Expose SSE app for mounting in FastAPI
mcp_app = mcp.sse_app()


if __name__ == "__main__":
    logger.info("Starting standalone FastMCP server on http://0.0.0.0:8000")
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8000,
    )
