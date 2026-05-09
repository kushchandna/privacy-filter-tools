# syntax=docker/dockerfile:1.7

# ── builder ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG OPF_REPO_URL=https://github.com/openai/privacy-filter.git
ARG OPF_REPO_REF=main

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# CPU-only torch wheel keeps the image small (no CUDA libs).
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

WORKDIR /opt
RUN git clone "$OPF_REPO_URL" privacy-filter \
    && git -C privacy-filter checkout "$OPF_REPO_REF"
WORKDIR /opt/privacy-filter
RUN pip install .

# ── runtime ───────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --shell /bin/bash redact

COPY --from=builder /opt/venv /opt/venv
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh

USER redact
WORKDIR /home/redact

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
