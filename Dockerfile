# Use Python 3.9 slim image for smaller size
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# CRITICAL: Set environment variables to prevent credential conflicts
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    # Clear Google Cloud credentials to prevent conflicts with API key
    GOOGLE_APPLICATION_CREDENTIALS="" \
    GCE_METADATA_HOST="metadata.google.internal.disabled" \
    GOOGLE_CLOUD_PROJECT="" \
    GCP_PROJECT="" \
    GCLOUD_PROJECT=""

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (informational only for Cloud Run)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level info