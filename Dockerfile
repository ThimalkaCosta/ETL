# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into an isolated prefix so we can copy them cleanly
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY run.py .

# Output directory (mounted as a volume in production to persist downloads)
RUN mkdir -p test-data

# Credentials are injected at runtime via environment variables:
#   COPERNICUSMARINE_USERNAME
#   COPERNICUSMARINE_PASSWORD
# Do NOT bake the .env file into the image.

# Run the ETL pipeline
CMD ["python", "run.py"]
