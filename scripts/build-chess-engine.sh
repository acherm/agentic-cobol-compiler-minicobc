#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-chessengine-cobol-codex}"
OUT_DIR="${2:-build/chess/compat}"

if [[ ! -d "$REPO_DIR/src" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p build/bin "$OUT_DIR"

./scripts/regenerate-chess-templates.sh "$REPO_DIR" > /dev/null
cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc

for stem in main board fen attack movegen makemove perft time eval search uci; do
    rm -f "$OUT_DIR/$stem.c"
    ./build/bin/minicobc "$REPO_DIR/src/$stem.cob" "$OUT_DIR/$stem.c"
done

cc \
    $(cob-config --cflags) \
    "$OUT_DIR/main.c" \
    "$OUT_DIR/board.c" \
    "$OUT_DIR/fen.c" \
    "$OUT_DIR/attack.c" \
    "$OUT_DIR/movegen.c" \
    "$OUT_DIR/makemove.c" \
    "$OUT_DIR/perft.c" \
    "$OUT_DIR/time.c" \
    "$OUT_DIR/eval.c" \
    "$OUT_DIR/search.c" \
    "$OUT_DIR/uci.c" \
    $(cob-config --libs) \
    -o "$OUT_DIR/cobochess"

echo "$OUT_DIR/cobochess"
