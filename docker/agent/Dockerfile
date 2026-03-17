# Agent container image — ephemeral sandbox for Primary Agent code execution.
#
# Epic 25 Story 25.1: Runs as non-root user `agent` (UID 1000).
# Reads task from /workspace/task.json, writes result to /workspace/result.json.
# No database access, no internal network access.

FROM python:3.12-slim AS base

# System dependencies for git operations and building native extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 1000)
RUN groupadd -g 1000 agent && \
    useradd -u 1000 -g agent -m -s /bin/bash agent

# Install project dependencies
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Copy source code
COPY src/ ./src/

# Create workspace volume mount point with correct ownership
RUN mkdir -p /workspace && chown agent:agent /workspace

# Switch to non-root user
USER agent

# Entrypoint: container runner reads task.json, runs agent, writes result.json
ENTRYPOINT ["python", "-m", "src.agent.container_runner"]
