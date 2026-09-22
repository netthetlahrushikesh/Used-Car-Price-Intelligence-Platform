# Multi-stage image for the Used Car Price Intelligence prediction API.
# Stage 1 installs deps; stage 2 runs uvicorn against the package app.

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt "uvicorn[standard]>=0.30"

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    USED_CAR_PREDICTION_LOG="/app/logs/predictions.jsonl"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY requirements.txt pyproject.toml app.py vercel.json ./
COPY src ./src
COPY artifacts/model ./artifacts/model
COPY schemas ./schemas
COPY config ./config

RUN mkdir -p /app/logs \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Keep the Vercel entry (app.py) intact; Docker serves the package ASGI app directly.
CMD ["uvicorn", "used_car_price_intelligence.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
