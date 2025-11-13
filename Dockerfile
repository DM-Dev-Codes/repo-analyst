FROM python:3.13-slim

WORKDIR /app

# Install git and uv
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Clone httpx repository
RUN git clone https://github.com/encode/httpx.git /app/httpx

# Copy project files
COPY . .

# Install dependencies
RUN uv sync --frozen --no-dev

# Expose main API port
EXPOSE 8001

# Set environment variables
ENV HTTPX_SOURCE_DIR=/app/httpx/httpx \
    MCP_SERVER_URL=http://localhost:8001/mcp/sse \
    PYTHONUNBUFFERED=1

# Health check - verify API is responding
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/docs').read()" || exit 1

# Run application
CMD [".venv/bin/python", "main.py"]