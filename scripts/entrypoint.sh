#!/usr/bin/env bash
set -euo pipefail

NON_TEXT_EXTENSIONS="pdf docx doc pptx ppt xlsx xls odt ods odp"

is_non_text() {
  local ext
  ext="$(echo "${1##*.}" | tr '[:upper:]' '[:lower:]')"
  for e in $NON_TEXT_EXTENSIONS; do
    [ "$e" = "$ext" ] && return 0
  done
  return 1
}

format_duration() {
  local total=$1
  if [ "$total" -lt 60 ]; then
    echo "${total}s"
  else
    echo "$((total / 60))m $((total % 60))s"
  fi
}

# Strip --cleanup from args before forwarding to opf
cleanup=false
filtered_args=()
for arg in "$@"; do
  if [ "$arg" = "--cleanup" ]; then
    cleanup=true
  else
    filtered_args+=("$arg")
  fi
done
set -- "${filtered_args[@]+"${filtered_args[@]}"}"

# Locate -f <file>; plan conversion + output paths (written next to the input)
new_args=()
input_file=""
input_dir=""
converted_file=""
host_converted_file=""
output_file=""
host_output_file=""
i=1
while [ $i -le $# ]; do
  arg="${!i}"
  if [ "$arg" = "-f" ] && [ $i -lt $# ] && [ -z "$output_file" ]; then
    j=$((i + 1))
    file="${!j}"
    input_file="$file"
    input_dir="${file%/*}"
    base="${file##*/}"
    stem="${base%.*}"
    ext="${base##*.}"
    # Resolve host directory mapping (set by bin/redact)
    file_idx="${input_dir##*/}"
    host_dir_var="REDACT_HOST_DIR_${file_idx}"
    host_dir="${!host_dir_var:-$input_dir}"
    if is_non_text "$file"; then
      converted_file="${input_dir}/${stem}.md"
      host_converted_file="${host_dir}/${stem}.md"
      new_args+=(-f "$converted_file")
      output_file="${input_dir}/${stem}.redacted.md"
      host_output_file="${host_dir}/${stem}.redacted.md"
    else
      new_args+=(-f "$file")
      output_file="${input_dir}/${stem}.redacted.${ext}"
      host_output_file="${host_dir}/${stem}.redacted.${ext}"
    fi
    i=$((i + 2))
    continue
  fi
  new_args+=("$arg")
  i=$((i + 1))
done

if [ -n "$output_file" ]; then
  conv_duration=""
  if [ -n "$converted_file" ]; then
    conv_start=$(date +%s)
    docling_log="$(mktemp)"
    if ! docling "$input_file" --output "$input_dir" --image-export-mode=placeholder \
        >"$docling_log" 2>&1; then
      cat "$docling_log" >&2
      rm -f "$docling_log"
      exit 1
    fi
    grep -v -E '^\[INFO\]|^Loading weights|^[[:space:]]*[0-9]+(\.[0-9]+)?%\|' \
      "$docling_log" >&2 || true
    rm -f "$docling_log"
    conv_duration=$(format_duration $(($(date +%s) - conv_start)))
  fi

  redact_start=$(date +%s)
  opf "${new_args[@]}" > "$output_file"
  redact_duration=$(format_duration $(($(date +%s) - redact_start)))

  echo "Redacted file written to ${host_output_file}."
  if [ -n "$converted_file" ]; then
    echo "Conversion to ${host_converted_file} took ${conv_duration}."
  fi
  echo "Redaction took ${redact_duration}."

  if [ -n "$converted_file" ] && "$cleanup"; then
    rm -f "$converted_file"
  fi
  exit
fi

exec opf "$@"
