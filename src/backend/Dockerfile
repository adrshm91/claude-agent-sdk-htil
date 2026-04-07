FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies as root
RUN uv sync --frozen

# Copy application code
COPY app/ ./app/

# Put the venv on PATH so executables can be found
ENV PATH="/app/.venv/bin:${PATH}"

# Create workspace directory and non-root user
RUN mkdir -p /var/tmp/workspace && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /var/tmp/workspace

USER appuser

# Expose port 6060
EXPOSE 6060

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6060/health || exit 1

# Direct uvicorn command
CMD ["/app/.venv/bin/uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "6060"]