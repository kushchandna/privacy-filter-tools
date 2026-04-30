# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash opf

ARG OPF_REPO_URL=https://github.com/openai/privacy-filter.git
ARG OPF_REPO_REF=main

# CPU-only torch wheel keeps the image small (no CUDA libs).
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

WORKDIR /opt
RUN git clone "$OPF_REPO_URL" privacy-filter \
    && git -C privacy-filter checkout "$OPF_REPO_REF"
WORKDIR /opt/privacy-filter
RUN pip install -e .

USER opf
WORKDIR /home/opf

ENTRYPOINT ["opf"]