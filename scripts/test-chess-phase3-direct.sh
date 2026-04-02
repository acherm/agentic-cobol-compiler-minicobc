#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHESS_DIR="$ROOT_DIR/external/agentic-chessengine-cobol-codex"
BUILD_DIR="$ROOT_DIR/build/chess-phase3-direct"
SPLIT_MAKEMOVE="$CHESS_DIR/src/makemove_minicobc_phase2.cob"
SPLIT_UNMAKEMOVE="$CHESS_DIR/src/unmakemove_minicobc_phase2.cob"

mkdir -p "$BUILD_DIR"

cobc -x -free -Wall "$ROOT_DIR/src/minicobc.cob" -o "$ROOT_DIR/build/bin/minicobc"

rm -f "$SPLIT_MAKEMOVE" "$SPLIT_UNMAKEMOVE"
awk -v out1="$SPLIT_MAKEMOVE" -v out2="$SPLIT_UNMAKEMOVE" '
    /^       IDENTIFICATION DIVISION\.$/ { ident += 1 }
    ident < 2 { print > out1; next }
    { print > out2 }
' "$CHESS_DIR/src/makemove.cob"

"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/board.cob" "$BUILD_DIR/board.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/fen.cob" "$BUILD_DIR/fen.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/attack.cob" "$BUILD_DIR/attack.c"
"$ROOT_DIR/build/bin/minicobc" "$SPLIT_MAKEMOVE" "$BUILD_DIR/makemove.c"
"$ROOT_DIR/build/bin/minicobc" "$SPLIT_UNMAKEMOVE" "$BUILD_DIR/unmakemove.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/time.cob" "$BUILD_DIR/time.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/eval.cob" "$BUILD_DIR/eval.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/movegen.cob" "$BUILD_DIR/movegen.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/uci.cob" "$BUILD_DIR/uci.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/search.cob" "$BUILD_DIR/search.c"

gcc -std=c11 -c "$BUILD_DIR/board.c" -o "$BUILD_DIR/board.o"
gcc -std=c11 -c "$BUILD_DIR/fen.c" -o "$BUILD_DIR/fen.o"
gcc -std=c11 -c "$BUILD_DIR/attack.c" -o "$BUILD_DIR/attack.o"
gcc -std=c11 -c "$BUILD_DIR/makemove.c" -o "$BUILD_DIR/makemove.o"
gcc -std=c11 -c "$BUILD_DIR/unmakemove.c" -o "$BUILD_DIR/unmakemove.o"
gcc -std=c11 -c "$BUILD_DIR/time.c" -o "$BUILD_DIR/time.o"
gcc -std=c11 -c "$BUILD_DIR/eval.c" -o "$BUILD_DIR/eval.o"
gcc -std=c11 -c "$BUILD_DIR/movegen.c" -o "$BUILD_DIR/movegen.o"
gcc -std=c11 -c "$BUILD_DIR/uci.c" -o "$BUILD_DIR/uci.o"
gcc -std=c11 -c "$BUILD_DIR/search.c" -o "$BUILD_DIR/search.o"
gcc -std=c11 "$ROOT_DIR/tests/chess/phase3_direct_harness.c" \
    "$BUILD_DIR/board.o" "$BUILD_DIR/fen.o" "$BUILD_DIR/attack.o" \
    "$BUILD_DIR/makemove.o" "$BUILD_DIR/unmakemove.o" "$BUILD_DIR/time.o" \
    "$BUILD_DIR/eval.o" "$BUILD_DIR/movegen.o" "$BUILD_DIR/uci.o" \
    "$BUILD_DIR/search.o" \
    -o "$BUILD_DIR/minicobc-phase3-direct"

"$BUILD_DIR/minicobc-phase3-direct" > "$BUILD_DIR/minicobc.out"

cobc -x -free \
    -I "$CHESS_DIR" \
    "$ROOT_DIR/tests/chess/phase3_direct_ref.cob" \
    "$CHESS_DIR/src/board.cob" \
    "$CHESS_DIR/src/fen.cob" \
    "$CHESS_DIR/src/attack.cob" \
    "$CHESS_DIR/src/makemove.cob" \
    "$CHESS_DIR/src/time.cob" \
    "$CHESS_DIR/src/eval.cob" \
    "$CHESS_DIR/src/movegen.cob" \
    "$CHESS_DIR/src/uci.cob" \
    "$CHESS_DIR/src/search.cob" \
    -o "$BUILD_DIR/gnucobol-phase3-direct"

"$BUILD_DIR/gnucobol-phase3-direct" > "$BUILD_DIR/gnucobol.out"
perl -pe 'if (/^([A-Z0-9-]+)\s+(.*)$/) { $label=$1; $rest=$2; $rest =~ s/ //g; $rest =~ s/\+0+(\d)/$1/g; $rest =~ s/\+(\d)/$1/g; $rest =~ s/-0+(\d)/-$1/g; $_="$label $rest\n"; }' \
    "$BUILD_DIR/gnucobol.out" > "$BUILD_DIR/gnucobol.norm"
perl -pe 'if (/^([A-Z0-9-]+)\s+(.*)$/) { $label=$1; $rest=$2; $rest =~ s/ //g; $rest =~ s/\+0+(\d)/$1/g; $rest =~ s/\+(\d)/$1/g; $rest =~ s/-0+(\d)/-$1/g; $_="$label $rest\n"; }' \
    "$BUILD_DIR/minicobc.out" > "$BUILD_DIR/minicobc.norm"
diff -u "$BUILD_DIR/gnucobol.norm" "$BUILD_DIR/minicobc.norm"
echo "phase3 direct ALPHABETA/QUIESCE build matched GnuCOBOL"
