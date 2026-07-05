# syntax=docker/dockerfile:1.7

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG OPF_REPO_URL=https://github.com/openai/privacy-filter.git
# Pinned upstream SHA — override at build time to test a newer commit.
ARG OPF_REPO_REF=f7f00ca7fb869683eb732c010299d901457f19c3
# Where docling's RapidOCR stores its ONNX weights. Override if the Python version changes.
ARG RAPIDOCR_MODELS_DIR=/opt/venv/lib/python3.11/site-packages/rapidocr/models

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

# Torch first so docling's extra-index resolves against the same index.
RUN pip install --index-url "$TORCH_INDEX_URL" torch

# Clone opf at the pinned SHA and install it into the venv.
WORKDIR /opt
RUN git clone "$OPF_REPO_URL" privacy-filter \
    && git -C privacy-filter checkout "$OPF_REPO_REF"
RUN pip install /opt/privacy-filter

RUN pip install docling --extra-index-url "$TORCH_INDEX_URL"

# python-docx needed by the M3 sample generator.
RUN pip install python-docx

# Install the redact-cli package from the local app/ directory.
COPY app/ /opt/app/
RUN pip install /opt/app

# Make rapidocr model dir writable so docling can download OCR weights at runtime.
RUN chmod -R a+w "$RAPIDOCR_MODELS_DIR"

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Re-declare so the value crosses the stage boundary, then expose it to the runtime
# so `bin/redact` can read RAPIDOCR_MODELS_DIR from the image env instead of hard-coding it.
ARG RAPIDOCR_MODELS_DIR=/opt/venv/lib/python3.11/site-packages/rapidocr/models

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    RAPIDOCR_MODELS_DIR="$RAPIDOCR_MODELS_DIR"

# Minimal shared-library deps needed by torch / docling at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

RUN useradd --create-home --shell /bin/bash redact

USER redact
WORKDIR /home/redact

ENTRYPOINT ["redact-cli"]
