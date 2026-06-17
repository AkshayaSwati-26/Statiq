# MoSPI Platform FastAPI Dockerfile
# Multi-stage build for production-grade security and size optimization

# ── Stage 1: Build virtual environment ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (necessary for compiling some wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Final runtime image ──────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime database dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code
COPY ai/ ./ai
COPY api/ ./api
COPY db/ ./db
COPY security/ ./security
COPY .env.example .env

# Expose default API port
EXPOSE 8000

# Non-root user for security compliance (OWASP/CIS benchmarks)
RUN useradd -u 10001 statiq-user && \
    chown -R statiq-user:statiq-user /app
USER statiq-user

# Start application gateway
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
