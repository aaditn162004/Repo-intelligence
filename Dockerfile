FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    make \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/

RUN mkdir -p /tmp/repos
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app /tmp/repos
USER appuser

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
