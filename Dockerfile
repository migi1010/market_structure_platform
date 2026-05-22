# Dockerfile for Market Structure Platform
# Support for daily stock analysis with market regime detection

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set timezone
ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data cache results

# Create non-root user
RUN useradd -m -u 1000 analyzer && chown -R analyzer:analyzer /app

USER analyzer

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "from data_provider.base import DataProviderManager; DataProviderManager()" || exit 1

# Default command
CMD ["python", "market_structure/analysis_scheduler.py", \
     "--stocks", "${STOCK_LIST}", \
     "--mode", "daily", \
     "--notify"]
