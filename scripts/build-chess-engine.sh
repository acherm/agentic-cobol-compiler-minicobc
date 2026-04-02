#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-chessengine-cobol-codex}"
OUT_DIR="${2:-build/chess/generic}"
SPLIT_MAKEMOVE="$REPO_DIR/src/makemove_minicobc_phase4.cob"
SPLIT_UNMAKEMOVE="$REPO_DIR/src/unmakemove_minicobc_phase4.cob"

if [[ ! -d "$REPO_DIR/src" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p build/bin "$OUT_DIR"

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc

rm -f "$SPLIT_MAKEMOVE" "$SPLIT_UNMAKEMOVE"
awk -v out1="$SPLIT_MAKEMOVE" -v out2="$SPLIT_UNMAKEMOVE" '
    /^       IDENTIFICATION DIVISION\.$/ { ident += 1 }
    ident < 2 { print > out1; next }
    { print > out2 }
' "$REPO_DIR/src/makemove.cob"

if [[ "${MINICOBC_OPT:-0}" = "1" ]]; then
    MINICOBC_CMD=(./build/bin/minicobc OPT)
else
    MINICOBC_CMD=(./build/bin/minicobc)
fi

for stem in board fen attack movegen perft time eval search uci main; do
    rm -f "$OUT_DIR/$stem.c"
done
rm -f "$OUT_DIR/makemove.c" "$OUT_DIR/unmakemove.c"

"${MINICOBC_CMD[@]}" "$REPO_DIR/src/board.cob" "$OUT_DIR/board.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/fen.cob" "$OUT_DIR/fen.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/attack.cob" "$OUT_DIR/attack.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/movegen.cob" "$OUT_DIR/movegen.c"
"${MINICOBC_CMD[@]}" "$SPLIT_MAKEMOVE" "$OUT_DIR/makemove.c"
"${MINICOBC_CMD[@]}" "$SPLIT_UNMAKEMOVE" "$OUT_DIR/unmakemove.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/perft.cob" "$OUT_DIR/perft.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/time.cob" "$OUT_DIR/time.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/eval.cob" "$OUT_DIR/eval.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/search.cob" "$OUT_DIR/search.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/uci.cob" "$OUT_DIR/uci.c"
"${MINICOBC_CMD[@]}" "$REPO_DIR/src/main.cob" "$OUT_DIR/main.c"

for stem in board fen attack movegen makemove unmakemove perft time eval search uci main; do
    gcc -std=c11 -O2 -c "$OUT_DIR/$stem.c" -o "$OUT_DIR/$stem.o"
done

gcc -std=c11 -O2 \
    "$OUT_DIR/board.o" \
    "$OUT_DIR/fen.o" \
    "$OUT_DIR/attack.o" \
    "$OUT_DIR/movegen.o" \
    "$OUT_DIR/makemove.o" \
    "$OUT_DIR/unmakemove.o" \
    "$OUT_DIR/perft.o" \
    "$OUT_DIR/time.o" \
    "$OUT_DIR/eval.o" \
    "$OUT_DIR/search.o" \
    "$OUT_DIR/uci.o" \
    "$OUT_DIR/main.o" \
    -o "$OUT_DIR/cobochess"

echo "$OUT_DIR/cobochess"
