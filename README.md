# Repo Analyst - HTTPX Code Explorer

AI agent that explains code from the [httpx](https://github.com/encode/httpx) library using MCP (Model Context Protocol) and OpenAI GPT-4.

## Overview

This project implements **Track A: Grounded Mode (MCP + Semi-Natural Language)** from the Repo Analyst assignment. It provides an HTTP API that accepts natural language queries about httpx code and returns detailed explanations with precise file citations.

## Features

- Precise symbol lookup (classes, functions, methods)
- Grounded responses with file paths and line ranges
- Security hardened (input validation, rate limiting, prompt injection protection)
- Structured logging, health checks, Docker support
- MCP-powered tool integration
- Fast AST-based indexing (509 symbols pre-loaded)

## Quick Start

### Prerequisites

- Docker
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Run

```bash
# Build image
docker build -t repo-analyst .

# Run with your API key
docker run -p 8001:8001 -e OPENAI_API_KEY=sk-proj-your-key-here repo-analyst
```

Server starts on `http://localhost:8001`

### Query the API

```bash
curl -X POST http://localhost:8001/query -d "Explain Client.get"
curl -X POST http://localhost:8001/query -d "What does AsyncHTTPTransport.handle_async_request do?"
curl -X POST http://localhost:8001/query -d "Explain Response.stream"
```

## Local Development (without Docker)

```bash
# Install dependencies
uv sync

# Clone httpx
git clone https://github.com/encode/httpx.git

# Configure environment
cp env_template .env
# Edit .env: Set OPENAI_API_KEY and MCP_SERVER_URL=http://localhost:8001/mcp/sse

# Run
python main.py
```

## Example Queries

### Query 1: Class Method

```bash
curl -X POST http://localhost:8001/query -d "Explain Client.get"
```

Response:
```json
{
  "symbols": ["Client.get"],
  "explanation": "The Client.get method sends HTTP GET requests...",
  "file_locations": ["_client.py:1036-1063"],
  "key_concepts": ["HTTP GET requests", "Parameter handling"]
}
```

### Query 2: Multiple Implementations

```bash
curl -X POST http://localhost:8001/query -d "Explain request"
```

Response (finds all implementations):
```json
{
  "symbols": ["request", "Client.request", "AsyncClient.request"],
  "file_locations": ["_api.py:39-120", "_client.py:771-825"],
  "explanation": "Multiple implementations across sync and async clients..."
}
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

**Flow:** User → FastAPI → Validation → Agent → MCP Tool → LookupBuilder → OpenAI → Response

## API Reference

**POST /query**

Request body: Plain text query string

Response:
```json
{
  "symbols": ["symbol1"],
  "explanation": "Detailed explanation...",
  "file_locations": ["file:line-range"],
  "key_concepts": ["concept1"]
}
```

Error responses: `400` (invalid query), `429` (rate limit), `500` (server error)

## Security Features

- Rate limiting: 10 requests/minute per IP
- Input validation: Max 300 characters
- Prompt injection protection: Blocks malicious patterns
- Path traversal prevention: Blocks `..`, `/etc/`, `file://`
- Read-only operations: No file modifications
- Agent guardrails: Scoped to httpx library only

## Testing

```bash
# Run integration test
python test_full_flow.py
```

Expected output:
```
INFO - ENVIRONMENT CHECK
INFO - OPENAI_API_KEY: ✓ Set
INFO - ✓ httpx directory found
INFO - TESTING LOOKUP BUILDER
INFO - ✓ Lookup table built: 509 symbols
INFO - TESTING SYMBOL QUERIES
INFO - ✓ Client.get: Found 1 result(s)
INFO - ✓ AsyncClient.get: Found 1 result(s)
INFO - TESTING MCP TOOL
INFO - ✓ MCP tool executed successfully
INFO - ✓ ALL TESTS PASSED
```

## Logging

- Console: INFO level
- app.log: All levels with rotation (10MB, 5 backups)

```bash
tail -f app.log
grep ERROR app.log*
```

## Project Structure

```
├── main.py              # Entry point
├── http_server.py       # FastAPI server with rate limiting
├── mcp_server.py        # MCP tool server
├── agent.py             # Pydantic AI agent
├── lookup.py            # AST-based symbol indexing
├── utils.py             # Input validation
├── metadata.py          # Pydantic models
└── Dockerfile           # Container definition
```

## Troubleshooting

**"OPENAI_API_KEY not found"**
- Docker: Pass `-e OPENAI_API_KEY=your-key` when running
- Local: Set in `.env` file

**"httpx directory not found"**
- Local: Run `git clone https://github.com/encode/httpx.git`

**Rate limit errors**
- Wait 1 minute or adjust in `http_server.py` line 21

## Assumptions & Limitations

**Assumptions:**
- Queries explicitly name symbols (e.g., "Client.get")
- Python 3.13+ runtime environment
- OpenAI API access

**Limitations:**
- Semi-natural language: Best with explicit symbol names
- Single repository: Only works with httpx
- Static analysis: Doesn't execute code or handle dynamic imports
- Rate limits: 10 requests/minute default

**Future Improvements:**
- Full natural language support
- Multi-repository support
- Caching layer for repeated queries
- Streaming responses
- Web UI frontend

## References

- [httpx](https://github.com/encode/httpx) - HTTP library for Python
- [Pydantic AI](https://ai.pydantic.dev/) - AI agent framework
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server implementation
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

