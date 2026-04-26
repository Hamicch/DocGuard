# ── builder ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy manifests first (maximises layer cache)
COPY pyproject.toml uv.lock ./

# Install production deps into an isolated venv
RUN uv sync --frozen --no-dev

# ── runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source
COPY src/ ./src/

EXPOSE 8000

# Local dev: run with uvicorn
# Lambda: handler is src.main.handler (Mangum)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
