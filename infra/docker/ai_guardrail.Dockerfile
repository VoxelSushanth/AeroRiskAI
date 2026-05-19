# Dockerfile for AI Guardrail Service
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

# Copy poetry files
COPY ai_guardrail/pyproject.toml ai_guardrail/poetry.lock ./

# Install dependencies
RUN poetry install --no-root --no-dev

# Copy source code
COPY ai_guardrail/ ./

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 aerorisk

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

USER aerorisk

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the AI service
CMD ["python", "-m", "uvicorn", "aerorisk.main:app", "--host", "0.0.0.0", "--port", "8000"]
