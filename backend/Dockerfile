FROM python:3.12-slim

# System dependencies for git, tree-sitter compilation, and scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    make \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Create repo storage directory
RUN mkdir -p /tmp/repos

# Non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app /tmp/repos
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
