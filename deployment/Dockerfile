# Multi-stage build for MSFT Agent Framework
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
RUN pip install --user --no-cache-dir .

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
# Using UID/GID 1000 for compatibility with Kubernetes runAsNonRoot
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Copy Python packages from builder to user-accessible location
COPY --from=builder /root/.local /home/appuser/.local

# Set PATH and Python environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/appuser

# Copy application code with proper ownership
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup config/ ./config/
COPY --chown=appuser:appgroup pyproject.toml .

# Set ownership of working directory
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER 1000:1000

# Set default command (override as needed)
CMD ["python", "-m", "src.orchestrator.main"]
