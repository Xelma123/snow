FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/server \
    DATA_DIR=/app/data \
    DEVICES_FILE=/app/personal/devices.yaml

# curl for HEALTHCHECK (compose + docker)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY server /app/server
COPY web /app/web
COPY personal /app/personal

RUN mkdir -p /app/data

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8787/api/v1/health || exit 1

# Root OK for bind-mounted ./data on homelab; non-root breaks host volume perms.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
