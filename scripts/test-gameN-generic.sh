#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-game15tictactoe}"
SOURCE="$REPO_DIR/gameN.cob"

if [[ ! -f "$SOURCE" ]]; then
    echo "missing source: $SOURCE" >&2
    exit 1
fi

mkdir -p build/bin build/generic-external build/generic-external-check

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc
./build/bin/minicobc "$SOURCE" build/generic-external/gameN.c

if ! rg -q "minicobc_argc" build/generic-external/gameN.c; then
    echo "gameN.c was not emitted by the generic minicobc path" >&2
    exit 1
fi

gcc -std=c11 build/generic-external/gameN.c -o build/generic-external/gameN
cobc -x "$SOURCE" -o build/generic-external/gameN.ref

build/generic-external/gameN 10 \
    > build/generic-external-check/gameN.10.mine.txt
build/generic-external/gameN.ref 10 \
    > build/generic-external-check/gameN.10.ref.txt
diff -u \
    build/generic-external-check/gameN.10.ref.txt \
    build/generic-external-check/gameN.10.mine.txt

build/generic-external/gameN 12 8 \
    > build/generic-external-check/gameN.12_8.mine.txt
build/generic-external/gameN.ref 12 8 \
    > build/generic-external-check/gameN.12_8.ref.txt
diff -u \
    build/generic-external-check/gameN.12_8.ref.txt \
    build/generic-external-check/gameN.12_8.mine.txt

build/generic-external/gameN 15 9 \
    > build/generic-external-check/gameN.15_9.mine.txt
build/generic-external/gameN.ref 15 9 \
    > build/generic-external-check/gameN.15_9.ref.txt
diff -u \
    build/generic-external-check/gameN.15_9.ref.txt \
    build/generic-external-check/gameN.15_9.mine.txt

echo "gameN.cob matched GnuCOBOL through the generic minicobc path"
