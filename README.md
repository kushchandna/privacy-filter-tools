# privacy-filter-tools

Docker packaging for the [OpenAI Privacy Filter](https://github.com/openai/privacy-filter) (`opf`) CLI — a bidirectional token-classification model for PII detection and masking.

This repo builds a self-contained image that clones the upstream `privacy-filter` source, installs the CPU PyTorch wheel, and exposes `opf` as the container entrypoint. The model checkpoint is downloaded on first run from the `openai/privacy-filter` HuggingFace repo.

## Build

```bash
docker build -t opf .
```

Optional build args:

- `OPF_REPO_URL` — upstream repo URL (default `https://github.com/openai/privacy-filter.git`)
- `OPF_REPO_REF` — branch, tag, or commit to check out (default `main`)

## Run

Mount a host directory into the container's `~/.opf` so the downloaded checkpoint persists across runs:

```bash
docker run -v ".data/opf:/home/opf/.opf" opf "My name is Alice"
```

The first invocation downloads the checkpoint into `.data/opf/privacy_filter/` on the host (a few GB). Subsequent runs reuse the cached weights.

### One-shot redaction

```bash
docker run -v ".data/opf:/home/opf/.opf" opf "Alice was born on 1990-01-02."
```

### Redact a file via stdin

```bash
cat input.txt | docker run -i -v ".data/opf:/home/opf/.opf" opf
```
OR
```bash
docker run -i -v ".data/opf:/home/opf/.opf" opf -f input.txt
```

### Run `opf` on cpu
```bash
docker run -v ".data/opf:/home/opf/.opf" opf --device cpu "Alice was born on 1990-01-02."
```