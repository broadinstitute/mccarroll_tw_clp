# Based on:
#   - https://docs.astral.sh/uv/guides/integration/docker/
#   - https://medium.com/@benitomartin/deep-dive-into-uv-dockerfiles-by-astral-image-size-performance-best-practices-5790974b9579

FROM ubuntu:24.04 AS builder

# Install tw

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl

RUN \
    curl -sSL \
        --output /usr/local/bin/tw \
        https://github.com/seqeralabs/tower-cli/releases/download/v0.38.0/tw-linux-x86_64 && \
    chmod +x /usr/local/bin/tw

# Install uv

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables for uv

ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1

WORKDIR /app

# Install the project dependencies using uv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app

# Compile the project using uv

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --compile

FROM ubuntu:24.04

COPY --from=builder /usr/local/bin/tw /usr/local/bin/tw
COPY --from=builder /python /python
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
