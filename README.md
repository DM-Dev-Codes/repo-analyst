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

## Quick Start (Docker)

### Prerequisites

- Docker
- **OpenAI API key** (required - get one from https://platform.openai.com/api-keys)

### 1. Configure Environment

**IMPORTANT:** You must set your OpenAI API key before running.

```bash
# Copy template and add your API key
cp env_template .env

# Edit .env and replace with your actual OpenAI API key
# Change: OPENAI_API_KEY=sk-your-key-here
# To:     OPENAI_API_KEY=sk-proj-...your-actual-key...
```

### 2. Build and Run

```bash
# Build image
docker build -t repo-analyst .

# Run container with your API key from .env file
docker run --env-file .env -p 8001:8001 repo-analyst
```

**Alternative:** Pass API key directly:
```bash
docker run -e OPENAI_API_KEY=sk-proj-your-key -p 8001:8001 repo-analyst
```

The server will start on `http://localhost:8001`

### 3. Query the API

```bash
curl -X POST http://localhost:8001/query -d "Explain Client.get"
curl -X POST http://localhost:8001/query -d "What does AsyncHTTPTransport.handle_async_request do?"
curl -X POST http://localhost:8001/query -d "Explain Response.stream"
```

## Local Development (without Docker)

```bash
# Install dependencies (uv creates venv automatically)
uv sync

# Configure environment
cp env_template .env
# Edit .env with your OPENAI_API_KEY

# Clone httpx repository (if not already present)
git clone https://github.com/encode/httpx.git

# Run server
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

## Docker Compose (Alternative)

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  repo-analyst:
    build: .
    ports:
      - "8001:8001"
    env_file:
      - .env
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", ".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/docs').read()"]
      interval: 30s
      timeout: 3s
      retries: 3
```

Run (make sure .env file exists with your API key):
```bash
docker-compose up --build
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
Create `.env` file from `env_template` and add your key

**"httpx directory not found"**  
Docker automatically clones it. For local dev: `git clone https://github.com/encode/httpx.git`

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

