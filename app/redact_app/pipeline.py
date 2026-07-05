from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from redact_app.convert import convert_to_markdown, is_non_text_file


@dataclass(frozen=True)
class RunConfig:
    text: str | None
    input_file: Path | None
    output_file: Path | None
    cleanup: bool
    force: bool
    device: str | None
    checkpoint: str | None


def _default_output_path(input_file: Path, non_text_input: bool) -> Path:
    if non_text_input:
        return input_file.with_name(f"{input_file.stem}.redacted.md")

    suffix = input_file.suffix or ".txt"
    return input_file.with_name(f"{input_file.stem}.redacted{suffix}")


def _intermediate_markdown_path(input_file: Path) -> Path:
    return input_file.with_name(f"{input_file.stem}.md")


def _validate_output_target(path: Path) -> None:
    parent = path.parent
    if not parent.exists():
        raise ValueError(f"output directory does not exist: {parent}")
    if not parent.is_dir():
        raise ValueError(f"output parent is not a directory: {parent}")


def _preflight_targets(targets: list[Path], force: bool) -> None:
    if force:
        return

    for path in targets:
        if path.exists():
            raise ValueError(f"refusing to overwrite existing file: {path}")


def _atomic_write(path: Path, content: str) -> None:
    _validate_output_target(path)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        tmp_name = handle.name
    os.replace(tmp_name, path)


def _opf_args(device: str | None, checkpoint: str | None) -> list[str]:
    args: list[str] = []

    selected_device = device
    if selected_device is None:
        try:
            import torch
        except ModuleNotFoundError:
            selected_device = "cpu"
        else:
            if not torch.cuda.is_available():
                selected_device = "cpu"

    if selected_device:
        args.extend(["--device", selected_device])
    if checkpoint:
        args.extend(["--checkpoint", checkpoint])

    return args


def _run_opf(
    opf_args: list[str],
    *,
    stdin_data: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = ["opf", *opf_args]
    return subprocess.run(
        command,
        input=stdin_data,
        capture_output=True,
        text=True,
        check=False,
    )


def _handle_opf_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.returncode == 0:
        return 0

    if result.stdout:
        sys.stderr.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def run(config: RunConfig) -> int:
    base_opf_args = _opf_args(config.device, config.checkpoint)

    if config.input_file is None:
        if config.text is not None:
            result = _run_opf([*base_opf_args, config.text])
        else:
            stdin_data = sys.stdin.read()
            result = _run_opf(base_opf_args, stdin_data=stdin_data)

        exit_code = _handle_opf_result(result)
        if exit_code != 0:
            return exit_code
        sys.stdout.write(result.stdout)
        return 0

    input_file = config.input_file
    non_text = is_non_text_file(input_file)
    output_file = config.output_file or _default_output_path(input_file, non_text)
    intermediate_file = _intermediate_markdown_path(input_file) if non_text else None

    preflight_paths = [output_file]
    if intermediate_file is not None:
        preflight_paths.append(intermediate_file)
    _preflight_targets(preflight_paths, config.force)

    file_for_opf = input_file
    if intermediate_file is not None:
        converted_markdown = convert_to_markdown(input_file)
        _atomic_write(intermediate_file, converted_markdown)
        file_for_opf = intermediate_file

    result = _run_opf([*base_opf_args, "-f", str(file_for_opf)])
    exit_code = _handle_opf_result(result)
    if exit_code != 0:
        return exit_code

    _atomic_write(output_file, result.stdout)
    print(f"Redacted file written to {output_file}.")

    if intermediate_file is not None and config.cleanup:
        intermediate_file.unlink(missing_ok=True)

    return 0
