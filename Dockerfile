# Financial Guardian AI - LangGraph Multi-Agent Backend
# Optimized for Hugging Face Spaces deployment

FROM python:3.11-slim

# Metadata
LABEL maintainer="FinKar Team"
LABEL description="AI-powered financial analysis with LangGraph multi-agent orchestration"
LABEL version="2.0.0"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY start.sh .

# Create data directory and set permissions for HF Spaces
RUN mkdir -p data && \
    chmod +x start.sh && \
    useradd -m -u 1000 user && \
    chown -R user:user /app

# Switch to non-root user (required by HF Spaces)
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start command
CMD ["./start.sh"]
