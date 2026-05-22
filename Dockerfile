FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /pesu-auth

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --frozen --no-install-project

COPY app ./app
RUN uv sync --no-dev --frozen

FROM python:3.12-slim-bookworm

WORKDIR /pesu-auth

COPY --from=builder /pesu-auth/.venv /pesu-auth/.venv
COPY app ./app

ENV PATH="/pesu-auth/.venv/bin:$PATH"

CMD ["python", "-m", "app.app"]
