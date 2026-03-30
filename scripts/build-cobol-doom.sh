#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-doom}"
OUT_DIR="${2:-build/doom/generic}"
MINICOBC_MODE="${MINICOBC_OPT:-0}"

if [[ ! -f "$REPO_DIR/doom.cob" || ! -f "$REPO_DIR/terminal-io.c" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p build/bin "$OUT_DIR"

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc

rm -f "$OUT_DIR/doom.c"
if [[ "$MINICOBC_MODE" = "1" ]]; then
    ./build/bin/minicobc OPT "$REPO_DIR/doom.cob" "$OUT_DIR/doom.c"
else
    ./build/bin/minicobc "$REPO_DIR/doom.cob" "$OUT_DIR/doom.c"
fi

gcc -O2 -Wall -std=c99 -o "$OUT_DIR/cobol-doom" "$OUT_DIR/doom.c" \
    "$REPO_DIR/terminal-io.c" -lm

echo "$OUT_DIR/cobol-doom"
