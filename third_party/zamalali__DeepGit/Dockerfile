# syntax=docker/dockerfile:1

# DeepGit - an agentic GitHub research engine.
# The image ships the CLI (`deepgit`) and the MCP server (`deepgit-mcp`),
# and by default runs the MCP server over HTTP so agents can call it.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy packaging metadata and sources first for better layer caching.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# Install DeepGit with the semantic-recall extra (LanceDB + fastembed, CPU-only).
RUN pip install ".[semantic]"

# Persist the semantic index outside the image. Mount a volume at /data to keep
# recall across container restarts.
ENV DEEPGIT_INDEX_DIR=/data/lancedb
RUN mkdir -p /data
VOLUME ["/data"]

# Run the MCP server over HTTP by default - ideal for agentic integrations.
# For local stdio clients (Claude Desktop, Cursor), override with:
#   docker run --rm -i -e GITHUB_API_KEY=... deepgit deepgit-mcp
ENV MCP_TRANSPORT=streamable-http \
    HOST=0.0.0.0 \
    PORT=8080

EXPOSE 8080

# Default: start the MCP server. To run a one-off CLI search instead:
#   docker run --rm -e GITHUB_API_KEY=... deepgit deepgit search "..."
ENTRYPOINT ["deepgit-mcp"]
