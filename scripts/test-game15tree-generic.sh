#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-game15tictactoe}"
SOURCE="$REPO_DIR/game15tree.cob"

if [[ ! -f "$SOURCE" ]]; then
    echo "missing source: $SOURCE" >&2
    exit 1
fi

mkdir -p build/bin build/generic-external build/generic-external-check

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc
./build/bin/minicobc "$SOURCE" build/generic-external/game15tree.c

if ! rg -q "minicobc_argc" build/generic-external/game15tree.c; then
    echo "game15tree.c was not emitted by the generic minicobc path" >&2
    exit 1
fi

gcc -std=c11 build/generic-external/game15tree.c -o build/generic-external/game15tree
cobc -x "$SOURCE" -o build/generic-external/game15tree.ref

build/generic-external/game15tree --depth 2 \
    > build/generic-external-check/game15tree.depth2.mine.txt
build/generic-external/game15tree.ref --depth 2 \
    > build/generic-external-check/game15tree.depth2.ref.txt
diff -u \
    build/generic-external-check/game15tree.depth2.ref.txt \
    build/generic-external-check/game15tree.depth2.mine.txt

echo "game15tree.cob matched GnuCOBOL through the generic minicobc path"
