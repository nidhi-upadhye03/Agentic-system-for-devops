FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user and add to docker group (GID 999 for docker socket access)
RUN groupadd -g 999 docker || true && \
    useradd -m -u 1000 -G docker autoresponse && \
    chown -R autoresponse:autoresponse /app
USER autoresponse

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the agent
CMD ["python", "-m", "app.main"]
