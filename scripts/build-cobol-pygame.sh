#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-pygame}"
OUT_DIR="${2:-build/pygame/compat}"
PROGRAM="${3:-flappy}"

if [[ "$PROGRAM" != "flappy" ]]; then
    echo "only flappy is currently supported" >&2
    exit 1
fi

if [[ ! -f "$REPO_DIR/examples/flappy.cob" || ! -f "$REPO_DIR/src/cpg.c" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p build/bin "$OUT_DIR"

./scripts/regenerate-pygame-templates.sh "$REPO_DIR" > /dev/null
cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc

rm -f "$OUT_DIR/flappy" "$OUT_DIR/flappy.c" "$OUT_DIR/flappy.c.h" \
    "$OUT_DIR/flappy.c.l.h" "$OUT_DIR/cpg.o"

./build/bin/minicobc "$REPO_DIR/examples/flappy.cob" "$OUT_DIR/flappy.c"

cc $(cob-config --cflags) $(sdl2-config --cflags) \
    -c "$REPO_DIR/src/cpg.c" -o "$OUT_DIR/cpg.o"

cc $(cob-config --cflags) $(sdl2-config --cflags) \
    "$OUT_DIR/flappy.c" "$OUT_DIR/cpg.o" \
    $(cob-config --libs) $(sdl2-config --libs) \
    -o "$OUT_DIR/flappy"

echo "$OUT_DIR/flappy"
