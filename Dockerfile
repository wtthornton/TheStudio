# ---- builder stage: compile native extensions ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Build-time deps (gcc, libpq-dev for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy vendor dependencies (ralph-sdk) and pyproject.toml
COPY vendor/ vendor/
COPY pyproject.toml .

# Rewrite the local-dev ralph-sdk path to the in-container vendor path.
# The local path (file:///C:/cursor/...) only works on the dev machine;
# inside Docker we use the vendored copy at /app/vendor/ralph-sdk.
RUN sed -i 's|ralph-sdk @ file:///C:/cursor/ralph/ralph-claude-code/sdk|ralph-sdk @ file:///app/vendor/ralph-sdk|' pyproject.toml

# Install into a virtual-env so we can copy just the site-packages
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir .

# Copy source (needed for the package install to resolve)
COPY src/ src/

# ---- runtime stage: slim final image ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime-only system deps (libpq for asyncpg, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source and entrypoint
COPY src/ src/
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
