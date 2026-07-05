# privacy-filter-tools

`privacy-filter-tools` is a practical privacy-filter CLI for detecting and masking PII in both plain text and common document formats. It uses the [OpenAI Privacy Filter](https://github.com/openai/privacy-filter) (`opf`) model under the hood and packages everything needed for local or containerized use. Upstream is licensed under [Apache 2.0](https://github.com/openai/privacy-filter/blob/main/LICENSE).

This repo provides:

- **`redact-cli`** — the core privacy-filter command-line tool: it auto-detects the device, converts non-text files (PDF, DOCX, …) to Markdown via [docling](https://github.com/DS4SD/docling), and runs `opf` over the result.
- **`bin/redact`** — a Docker-first launcher for `redact-cli` that rewrites host paths into container paths, so you can run the same CLI without setting up Python locally.
- A two-stage Docker image that keeps the runtime layer meaningfully smaller than a naïve single-stage build.

## Quick start (Docker)

```bash
# 1. Build
docker build -t redact .

# 2. Add bin/ to PATH (or use ./bin/redact)
export PATH="$PWD/bin:$PATH"

# 3. Redact a string
redact "My name is Alice and my email is alice@example.com"

# 4. Redact a file (PDF, DOCX, etc.)
redact -f contract.docx
```

The checkpoint (~2 GB) is downloaded from HuggingFace on the first run and cached in `.data/checkpoints/`. Subsequent runs reuse it.

## Build

```bash
docker build -t redact .
```

Build arguments:

| Argument | Default | Purpose |
|---|---|---|
| `OPF_REPO_URL` | `https://github.com/openai/privacy-filter.git` | Upstream repo URL |
| `OPF_REPO_REF` | `f7f00ca7fb869683eb732c010299d901457f19c3` | Pinned upstream SHA; override to test a newer commit |
| `TORCH_INDEX_URL` | `https://download.pytorch.org/whl/cpu` | PyTorch wheel index; pass a cu12x index for a CUDA image |

## `bin/redact` wrapper

The `bin/redact` script rewrites `-f <host_path>`, `-o <host_path>`, and `--checkpoint <host_path>` arguments into container-internal paths, mounts the relevant directories, and calls `docker run`. Use it exactly as you would use `redact-cli` directly.

### Configuration via `bin/.env`

```bash
cp bin/.env.example bin/.env
# edit bin/.env as needed
```

`bin/.env` is sourced on every invocation. It is gitignored.

| Variable | Default | Purpose |
|---|---|---|
| `HF_TOKEN` | — | HuggingFace token, forwarded into the container |
| `REDACT_CHECKPOINT_DIR` | `.data/checkpoints` | Host directory where checkpoint caches are stored across runs |
| `REDACT_IMAGE` | `redact:latest` | Image tag to run |
| `REDACT_DOCKER_ARGS` | — | Extra flags for `docker run` itself, inserted **before** the image (e.g. `--gpus all`) |
| `REDACT_ARGS` | — | Extra CLI arguments for `redact-cli` inside the container, appended **after** the image (e.g. `--device cpu`) |

### Usage examples

```bash
# Redact a string
redact "Alice was born on 1990-01-02."

# Pipe stdin
cat report.txt | redact

# Redact a document (PDF, DOCX, PPTX, …)
redact -f contract.docx

# Custom output path
redact -f contract.docx -o redacted/contract.md

# Delete the intermediate .md after redaction
redact -f contract.docx --cleanup

# Overwrite existing output files
redact -f contract.docx --force

# Point at a local checkpoint
redact -f contract.docx --checkpoint /path/to/my-checkpoint
```

`--force` overrides the safety check that refuses to overwrite existing output or intermediate files. Without it, a second run on the same file exits 1 and names the file it would overwrite.

## Native install (no Docker)

Use this path on Apple Silicon with MPS acceleration, or when Docker is not available.

```bash
pip install git+https://github.com/openai/privacy-filter@f7f00ca7fb869683eb732c010299d901457f19c3
pip install docling
pip install ./app

redact-cli -f contract.docx
```

`redact-cli` auto-detects the device: it defaults to `cpu` when CUDA is unavailable, or you can pass `--device mps` / `--device cuda` explicitly.

## Hardware notes

| Hardware | How to use |
|---|---|
| **CPU** | Default image; no extra flags needed |
| **NVIDIA CUDA** | Build with `--build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121`, then run with `REDACT_DOCKER_ARGS="--gpus all"` (docker run flag) and `REDACT_ARGS="--device cuda"` (redact-cli flag) |
| **Apple MPS** | Containers cannot access the Apple GPU; use the native install path with `--device mps` |

## Smoke test

```bash
# Build the image first, then:
python tests/smoke_test.py
```

The test generates a synthetic PII document (`tests/output/sample.docx`), redacts it, and verifies that opf placeholders are present, raw PII is absent, the overwrite guard works, and `--force --cleanup` leaves only the `.redacted.md`. Output files are gitignored and never committed.