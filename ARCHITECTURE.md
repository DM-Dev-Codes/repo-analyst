# Architecture Documentation

## System Overview

This project implements an **AI agent** for code explanation using the **Model Context Protocol (MCP)** architecture pattern. The system is designed for emphasis on concise citations and read-only operations.

## Design Philosophy

1. Single-process architecture with mounted MCP server(Cookbook pattern)
2. Every answer includes file:line citations
3. Multiple validation layers, rate limiting, read-only, Gaurdrails
4. Logging, health checks, error handling
5. One-command start, clear documentation

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User/Client                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST
                           │ /query
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI HTTP Server                       │
│                     (http_server.py)                         │
│                                                               │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐     │
│  │ Rate Limit │→ │  Validation  │→ │ Dependency      │     │
│  │ (10/min)   │  │  (utils.py)  │  │ Injection       │     │
│  └────────────┘  └──────────────┘  └─────────────────┘     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              CodeLocatorAgent (agent.py)                     │
│              Powered by Pydantic AI                          │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  System Prompt: Guardrails + Instructions          │    │
│  │  - Only explain httpx code                          │    │
│  │  - Always cite file:line                            │    │
│  │  - Handle multiple implementations(return all)                  │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│         MCP Server (Mounted at /mcp)                         │
│              (mcp_server.py)                                 │
│                                                               │
│  Tool: get_source_code(symbols: list[str])                   │
│    ├─ Input: ["Client.get", "AsyncClient.get"]              │
│    └─ Output: SymbolLookupResult                             │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         LookupBuilder (lookup.py)                     │   │
│  │                                                        │   │
│  │  1. Initialization (Module Load)                      │   │
│  │     └─ Scan httpx/httpx/*.py                          │   │
│  │     └─ Parse with AST                                 │   │
│  │     └─ Build lookup_table: 509 symbols               │   │
│  │                                                        │   │
│  │  2. Query Processing                                  │   │
│  │     └─ Exact match: "Client.get"                      │   │
│  │     └─ Suffix match: ".get" → all *.get methods       │   │
│  │                                                        │   │
│  │  3. Code Retrieval                                    │   │
│  │     └─ Read file at exact line range                  │   │
│  │     └─ Return code + metadata                         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    OpenAI GPT-4o                             │
│                                                               │
│  Receives: Tool results + System prompt                      │
│  Returns: CodeExplanation (structured)                       │
│    ├─ symbols: ["Client.get"]                                │
│    ├─ explanation: "..."                                     │
│    ├─ file_locations: ["_client.py:1036-1063"]               │
│    └─ key_concepts: [...]                                    │
└───────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. HTTP Server (`http_server.py`)

**Responsibilities:**
- Accept POST requests at `/query`
- Rate limiting (10 requests/minute per IP)
- Input validation
- Dependency injection for agent
- Error handling and responses

**Design Decisions:**
- **FastAPI**: Modern, async, auto-generated docs(swagger)
- **SlowAPI**: Memory-based rate limiting (simple)
- **Lifespan management**: Single agent instance, graceful shutdown
- **Pydantic models**: Automatic request/response validation
- **Security**: Multi-layer defense (see Security Model section)

### 2. MCP Server (`mcp_server.py`)

**Responsibilities:**
- Expose `get_source_code` tool to agent
- Query LookupBuilder for symbols
- Return structured results with code and citations

**Design Decisions:**
- **Mounted not separate**: Single process, internal routing (can be decoupled for microservice/multiprocessing)
- **FastMCP**: Official MCP server implementation
- **Async wrapping**: `asyncio.to_thread()` for blocking I/O

### 3. Agent (`agent.py`)

**Responsibilities:**
- Orchestrate query processing
- Call MCP tools
- Use LLM to generate explanations
- Return structured CodeExplanation

**Design Decisions:**
- **Pydantic AI**: Type-safe, structured outputs
- **Fresh agent per query**: Thread-safe, no state pollution
- **Strict system prompt**: Guardrails prevent misuse
- **Output validation**: Pydantic ensures required fields

### 4. Lookup Builder (`lookup.py`)

**Responsibilities:**
- Index all Python symbols in httpx (509 symbols)
- Support fast symbol lookup (exact match + suffix match)
- Retrieve code from files

**Design Decisions:**
- **AST-based parsing**: Accurate, no regex hacks
- **Module-level initialization**: Build once, query many times
- **Absolute paths**: Works in any environment

### 5. Data Models (`metadata.py`)

**Pydantic Models:** SymbolMetadata, SymbolMatch, SymbolLookupResult, CodeExplanation

**Benefits:** Runtime validation, JSON serialization, type safety

## Data Flow

**Request Path:** User → FastAPI → Agent → MCP Tool → LookupBuilder → OpenAI → Response

**Error Handling:** Symbol not found returns error message, rate limit returns 429, invalid input raises 400

## Design Decisions

### 1. Single Process Architecture
**Decision:** Mount MCP at `/mcp` path (not separate containers)  
**Rationale:** Simpler deployment, faster communication, single log stream  
**Trade-off:** Can't scale MCP independently (not needed for this use case)

### 2. AST Parsing
**Decision:** Use Python's `ast` module (not regex)  
**Rationale:** Accurate, extracts docstrings/line numbers, handles nested structures  
**Trade-off:** Slower than regex (but only runs once at startup)

### 3. Eager Initialization
**Decision:** Build lookup table at module import  
**Rationale:** Pay cost once at startup, O(1) queries  
**Trade-off:** Longer startup, but all queries are fast


## Scalability Considerations

**Current Limits:**
- Single process (no horizontal scaling)
- In-memory rate limiting (resets on restart)


**To Scale:**
1. **Multiple instances:** Add Redis for rate limiting
2. **High traffic:** Separate MCP server process
3. **Large codebases:** Add caching layer (Redis)
4. **Real-time:** Add WebSocket support for streaming

## Security Model

**Defense in Depth:**
```
Layer 1: Rate Limiting (10/min)
Layer 2: Input Length (max 300 chars)
Layer 3: Pattern Matching (blocks injection)
Layer 4: Path Traversal Prevention
Layer 5: Agent Guardrails (system prompt)
Layer 6: Read-Only Operations (no file writes)
```

**Threat Model:**
-  Protected: Prompt injection, path traversal, abuse
-  Protected: Code execution, file modification
-  Partial: DDoS (rate limit helps but not sufficient)
- Not protected: Sophisticated adversarial prompts (would need more AI safety)



## Testing Strategy

**Integration Test:** `test_full_flow.py`
- Tests: Lookup building, symbol queries, MCP tool

**Manual Testing:**
```bash
python main.py
curl -X POST http://localhost:8001/query -d "Explain Client.get"
```

## Deployment

**Docker:**
```dockerfile
FROM python:3.13-slim
# Clone httpx during build
# Install dependencies with uv
# Single CMD: python main.py
```

**Environment Variables:**
```bash
OPENAI_API_KEY=required
MCP_SERVER_URL=http://localhost:8001/mcp/sse
HTTPX_SOURCE_DIR=./httpx/httpx
```

**Health Check:**
```bash
curl http://localhost:8001/docs
→ 200 OK = healthy
```

## Future Enhancements

1. **Full NL support:** Accept "how to make GET request" queries
2. **Multi-repo:** Support any Python repository
3. **Caching:** Cache LLM responses for repeated queries
4. **Streaming:** SSE for real-time responses
5. **Web UI:** React frontend for better UX
6. **Analytics:** Track popular queries, error rates
7. **A/B testing:** Compare different prompts/models

## References

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Python AST Module](https://docs.python.org/3/library/ast.html)

