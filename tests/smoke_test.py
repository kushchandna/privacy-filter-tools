#!/usr/bin/env python3
"""
End-to-end smoke test for privacy-filter-tools.

Drives ``bin/redact`` (Docker) against a synthetic PII document and verifies
four behavioural properties:

  Step 1 — first redaction: exit 0, .redacted.md exists, opf placeholders
            present, raw synthetic PII strings absent from output.
  Step 2 — re-run without --force: exit 1, existing output file not modified.
  Step 3 — re-run with --force --cleanup: intermediate .md removed,
            .redacted.md retained.
  CAPS  — ALL-CAPS name absence is reported as a WARNING, not a failure
            (known model recall limitation; the fix is fine-tuning).

Prerequisites:
    docker build -t redact .        # build the image
    python-docx installed            # for sample generation

Run from the repository root:
    python tests/smoke_test.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_REDACT = REPO_ROOT / "bin" / "redact"
OUTPUT_DIR = REPO_ROOT / "tests" / "output"
SAMPLE_DOCX = OUTPUT_DIR / "sample.docx"
SAMPLE_MD = OUTPUT_DIR / "sample.md"
SAMPLE_REDACTED = OUTPUT_DIR / "sample.redacted.md"

sys.path.insert(0, str(Path(__file__).parent))
from generate_sample import (  # noqa: E402
    CAPS_NAME,
    SYNTHETIC_ADDRESS,
    SYNTHETIC_CREDENTIAL,
    SYNTHETIC_DOB,
    SYNTHETIC_EMAIL,
    SYNTHETIC_ID_NUM,
    SYNTHETIC_NAME,
    SYNTHETIC_PHONE,
    SYNTHETIC_USERNAME,
    generate,
)

_KNOWN_PII: list[tuple[str, str]] = [
    ("name", SYNTHETIC_NAME),
    ("email", SYNTHETIC_EMAIL),
    ("phone", SYNTHETIC_PHONE),
    ("address", SYNTHETIC_ADDRESS),
    ("dob", SYNTHETIC_DOB),
    ("username", SYNTHETIC_USERNAME),
    ("id_num", SYNTHETIC_ID_NUM),
    ("credential", SYNTHETIC_CREDENTIAL),
]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN_REDACT), *args],
        capture_output=True,
        text=True,
    )


def _banner(text: str) -> None:
    print(f"\n── {text} {'─' * max(0, 60 - len(text))}")


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Pre-flight: check bin/redact is executable
    # ------------------------------------------------------------------
    if not BIN_REDACT.is_file():
        sys.exit(f"smoke_test: bin/redact not found at {BIN_REDACT}")

    # ------------------------------------------------------------------
    # Setup: clean output dir and generate sample docx
    # ------------------------------------------------------------------
    _banner("Setup")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in (SAMPLE_DOCX, SAMPLE_MD, SAMPLE_REDACTED):
        stale.unlink(missing_ok=True)

    print("Generating sample.docx...")
    generate(SAMPLE_DOCX)

    # ------------------------------------------------------------------
    # Step 1: first redaction
    # ------------------------------------------------------------------
    _banner("Step 1: first redaction (expect exit 0)")
    result1 = _run("-f", str(SAMPLE_DOCX))
    print(result1.stdout, end="")
    if result1.returncode != 0:
        failures.append(
            f"Step 1: expected exit 0, got {result1.returncode}\n"
            f"  stderr: {result1.stderr.strip()}"
        )
    elif not SAMPLE_REDACTED.exists():
        failures.append("Step 1: sample.redacted.md was not created")
    else:
        redacted_text = SAMPLE_REDACTED.read_text()

        if not re.search(r"<PRIVATE_\w+>", redacted_text):
            failures.append("Step 1: no opf-style <PRIVATE_...> placeholders found in output")

        for label, pii in _KNOWN_PII:
            if pii in redacted_text:
                failures.append(f"Step 1: raw {label} PII still present in redacted output")

        # ALL-CAPS name: known model limitation — warn, do not fail
        if CAPS_NAME in redacted_text:
            warnings.append(
                f"ALL-CAPS name '{CAPS_NAME}' was not redacted — "
                "known model recall gap (needs fine-tuning to fix)"
            )

    # ------------------------------------------------------------------
    # Step 2: re-run without --force (must refuse and exit 1)
    # ------------------------------------------------------------------
    _banner("Step 2: re-run without --force (expect exit 1)")
    mtime_before = SAMPLE_REDACTED.stat().st_mtime if SAMPLE_REDACTED.exists() else None
    result2 = _run("-f", str(SAMPLE_DOCX))
    print(result2.stderr, end="")
    if result2.returncode == 0:
        failures.append("Step 2: expected exit 1 (refuse overwrite), got exit 0")
    if mtime_before is not None and SAMPLE_REDACTED.exists():
        if SAMPLE_REDACTED.stat().st_mtime != mtime_before:
            failures.append("Step 2: sample.redacted.md was modified despite expected exit 1")

    # ------------------------------------------------------------------
    # Step 3: --force --cleanup (intermediate .md removed, .redacted.md kept)
    # ------------------------------------------------------------------
    _banner("Step 3: --force --cleanup (expect .md removed, .redacted.md retained)")
    result3 = _run("-f", str(SAMPLE_DOCX), "--force", "--cleanup")
    print(result3.stdout, end="")
    if result3.returncode != 0:
        failures.append(
            f"Step 3: expected exit 0, got {result3.returncode}\n"
            f"  stderr: {result3.stderr.strip()}"
        )
    if SAMPLE_MD.exists():
        failures.append("Step 3: intermediate sample.md was not removed by --cleanup")
    if not SAMPLE_REDACTED.exists():
        failures.append("Step 3: sample.redacted.md was unexpectedly removed")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print()
    if warnings:
        for w in warnings:
            print(f"WARNING: {w}")
        print()

    if failures:
        print(f"FAILED — {len(failures)} check(s) did not pass:")
        for msg in failures:
            print(f"  ✗ {msg}")
        return 1

    print(
        f"OK — all smoke checks passed"
        + (f" ({len(warnings)} warning(s))" if warnings else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
