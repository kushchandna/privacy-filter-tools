from __future__ import annotations

import argparse
import sys
from pathlib import Path

from redact_app.pipeline import RunConfig, run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="redact-cli")
    parser.add_argument("text", nargs="?", help="Text to redact")
    parser.add_argument(
        "-f",
        "--file",
        action="append",
        help="File input path; repeat -f/--file to redact multiple files in one run",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output path; only valid with a single -f/--file",
    )
    parser.add_argument("--cleanup", action="store_true", help="Delete intermediate .md")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting output/intermediate files",
    )
    parser.add_argument("--device", help="Device passed to opf (e.g. cpu, cuda, mps)")
    parser.add_argument("--checkpoint", help="Checkpoint path passed to opf")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    files = args.file or []

    if files and args.text is not None:
        parser.error("cannot use positional text and -f/--file together")

    if args.output and not files:
        parser.error("-o/--output requires -f/--file")

    if args.output and len(files) > 1:
        parser.error("-o/--output cannot be used with multiple -f/--file inputs")

    if not files and args.text is None and sys.stdin.isatty():
        parser.error("provide text, pipe stdin, or use -f/--file")

    input_files = [Path(f).expanduser() for f in files]
    output_file = Path(args.output).expanduser() if args.output else None

    config = RunConfig(
        text=args.text,
        input_files=input_files,
        output_file=output_file,
        cleanup=args.cleanup,
        force=args.force,
        device=args.device,
        checkpoint=args.checkpoint,
    )

    try:
        return run(config)
    except ValueError as exc:
        print(f"redact-cli: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

