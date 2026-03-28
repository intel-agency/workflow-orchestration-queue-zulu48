# Dockerfile for workflow-orchestration-queue
# Build stage for Python dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv pip install --system -e .

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code (must be before pip install for editable installs)
COPY src/ ./src/
COPY pyproject.toml ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose port for notifier service
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "src.notifier_service:app", "--host", "0.0.0.0", "--port", "8000"]
