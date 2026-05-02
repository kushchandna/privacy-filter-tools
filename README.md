# privacy-filter-tools

Docker packaging named `redact` for the [OpenAI Privacy Filter](https://github.com/openai/privacy-filter) (`opf`) CLI — a bidirectional token-classification model for PII detection and masking.

This repo builds a self-contained image that clones the upstream `privacy-filter` source, installs the CPU PyTorch wheel, and exposes `redact` as the container entrypoint. The model checkpoint is downloaded on first run from the `openai/privacy-filter` HuggingFace repo.

## Build

```bash
docker build -t redact .
```

Optional build args:

- `OPF_REPO_URL` — upstream repo URL (default `https://github.com/openai/privacy-filter.git`)
- `OPF_REPO_REF` — branch, tag, or commit to check out (default `main`)

## Run via `bin/redact` wrapper

The repo ships a `bin/redact` shell script that wraps `docker run` so you can invoke `redact` like a native CLI. Add it to your `PATH`:

```bash
export PATH="$PWD/bin:$PATH"
redact "My name is Alice"
```

The wrapper mounts a host directory at `/home/redact/.opf` for the checkpoint cache, forwards `HF_TOKEN` into the container if set, and auto-attaches a TTY when stdin is a terminal.

### Configuration via `bin/.env`

Copy the template and uncomment the variables you want:

```bash
cp bin/.env.example bin/.env
```

`bin/.env` is sourced by `bin/opf` on every run. It is gitignored.

| Variable              | Default              | Purpose                                                          |
|-----------------------|----------------------|------------------------------------------------------------------|
| `HF_TOKEN`            | —                    | HuggingFace token, forwarded into the container                  |
| `REDACT_CHECKPOINT_DIR`  | `.data/checkpoints`  | Host directory mounted at `/home/redact/.opf` (checkpoint cache)    |
| `REDACT_IMAGE`           | `redact:latest`         | Image tag to run                                                 |
| `REDACT_DOCKER_RUN_ARGS` | —                    | Extra args appended to the `opf` command (e.g. `--device cpu`)   |

## Run via raw `docker run`

Mount a host directory into the container's `~/.opf` so the downloaded checkpoint persists across runs:

```bash
docker run -v ".data/checkpoints:/home/redact/.opf" redact "My name is Alice"
```

The first invocation downloads the checkpoint into `.data/checkpoints/privacy_filter/` on the host (a few GB). Subsequent runs reuse the cached weights.

### One-shot redaction

```bash
docker run -v ".data/checkpoints:/home/redact/.opf" redact "Alice was born on 1990-01-02."
```

### Redact a file via stdin

```bash
cat input.txt | docker run -i -v ".data/checkpoints:/home/redact/.opf" redact
```
OR
```bash
docker run -i -v ".data/checkpoints:/home/redact/.opf" redact -f input.txt
```

### Run `opf` on cpu
```bash
docker run -v ".data/checkpoints:/home/redact/.opf" redact --device cpu "Alice was born on 1990-01-02."
```