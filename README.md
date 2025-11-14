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

## Quick Start (Docker) - Simplest Setup!

### Prerequisites

- Docker
- OpenAI API key (get one from https://platform.openai.com/api-keys)

### Build and Run

**That's it! Just pass your OpenAI API key:**

```bash
# Build image (downloads httpx and sets up everything)
docker build -t repo-analyst .

# Run with your API key
docker run -p 8001:8001 \
  -e OPENAI_API_KEY=sk-proj-your-actual-key-here \
  repo-analyst
```

**Optional:** If you prefer storing your key in a file:
```bash
# Create .env and add your key
echo "OPENAI_API_KEY=sk-proj-your-key" > .env

# Run (extracts key from .env)
docker run -p 8001:8001 \
  -e OPENAI_API_KEY="$(grep '^OPENAI_API_KEY=' .env | cut -d'=' -f2- | tr -d '\"')" \
  repo-analyst
```

**Docker handles everything:** httpx clone, paths, MCP URL. You only provide the API key!

The server will start on `http://localhost:8001`

### 3. Query the API

```bash
curl -X POST http://localhost:8001/query -d "Explain Client.get"
curl -X POST http://localhost:8001/query -d "What does AsyncHTTPTransport.handle_async_request do?"
curl -X POST http://localhost:8001/query -d "Explain Response.stream"
```

## Local Development (without Docker)

**For local dev, you need to set up .env and clone httpx manually:**

```bash
# 1. Install dependencies (uv creates venv automatically)
uv sync

# 2. Clone httpx repository
git clone https://github.com/encode/httpx.git

# 3. Configure environment - REQUIRED for local dev
cp env_template .env

# 4. Edit .env and set these REQUIRED values:
#    OPENAI_API_KEY=sk-proj-your-actual-key
#    MCP_SERVER_URL=http://localhost:8001/mcp/sse
#    (HTTPX_SOURCE_DIR defaults to ./httpx/httpx - usually no need to change)

# 5. Run server
python main.py
```

**Note:** Docker users skip all this - Docker handles cloning, paths, and MCP URL automatically!

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

## Docker Compose (Alternative)

**Just pass your OpenAI API key:**

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  repo-analyst:
    build: .
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", ".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/docs').read()"]
      interval: 30s
      timeout: 3s
      retries: 3
```

Run with your API key:
```bash
# Pass key directly
OPENAI_API_KEY=sk-proj-your-key docker-compose up --build

# Or load from .env file
export $(grep '^OPENAI_API_KEY=' .env | xargs) && docker-compose up --build
```

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
- **Docker:** Pass `-e OPENAI_API_KEY=your-key` when running container
- **Local dev:** Create `.env` file from `env_template` and add your key

**"MCP_SERVER_URL not found"**  
- **Docker:** Nothing needed, auto-configured
- **Local dev:** Add `MCP_SERVER_URL=http://localhost:8001/mcp/sse` to your `.env`

**"httpx directory not found"**  
- **Docker:** Automatically cloned, shouldn't happen
- **Local dev:** Run `git clone https://github.com/encode/httpx.git`

**Rate limit errors**  
Wait 1 minute or adjust limit in `http_server.py` line 21

**Docker health check failing**  
Increase `start-period` in Dockerfile if initialization takes longer

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

