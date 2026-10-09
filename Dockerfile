# 价投宝 application image: API, worker, scheduler and migrations all run from this one image.
# Build from the repository root:  docker build -t vip-app .
# Secrets are never baked in: they arrive as environment variables at run time (deploy/secrets/app.env).

FROM python:3.12-slim-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --home-dir /app --shell /usr/sbin/nologin vip
ENV PATH=/app/backend/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Asia/Shanghai
WORKDIR /app/backend
COPY --from=build /app/backend/.venv /app/backend/.venv
# Runtime reads config/*.json and examples/ relative to the repository root.
COPY config /app/config
COPY examples /app/examples
COPY backend /app/backend
RUN mkdir -p /app/raw-data && chown vip:vip /app/raw-data
USER vip
EXPOSE 8766
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8766/api/health', timeout=4).status == 200 else 1)"
# Only the reverse proxy can reach this port (private compose network), so trusting its
# X-Forwarded-* headers is safe; the port is never published on the host.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8766", "--workers", "2", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
