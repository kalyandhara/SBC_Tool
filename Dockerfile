# SBC Tool - Dockerfile
# Multi-stage build for smaller production image

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Toolchain for wheels built from source (pyswisseph has C code).
# --no-install-recommends drops libc6-dev from plain `gcc`, which is why the
# build failed at `#include <math.h>`; build-essential brings it along.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser appuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code (see .dockerignore for what stays out)
COPY --chown=appuser:appuser . .

# Writable data directory (SQLite caches, profiles, forecast ledger)
RUN mkdir -p data/kp data/output && chown -R appuser:appuser data

# City search database (GeoNames, cities >= 15,000 people). Uses data/geonames/ when it
# was copied in; otherwise downloads about 3.5 MB.
RUN python scripts/seed_cities.py && chown appuser:appuser data/cities.db

# Switch to non-root user
USER appuser

# Add user packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check: python:slim has no curl, so use the standard library.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5).status == 200 else 1)"

# Run with gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
