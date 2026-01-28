FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

ADD . /app

FROM python:3.14-slim-bookworm

WORKDIR /app

COPY --from=builder /app /app

# Ensure we use the virtualenv
ENV PATH="/app/.venv/bin:$PATH"

ENV DB_HOST=db
ENV DB_PORT=5432
ENV PYTHONPATH=/app/backend/src

EXPOSE 8000

# Start uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
