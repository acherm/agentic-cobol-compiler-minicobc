#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHESS_DIR="$ROOT_DIR/external/agentic-chessengine-cobol-codex"
BUILD_DIR="$ROOT_DIR/build/chess-phase1"

mkdir -p "$BUILD_DIR"

cobc -x -free -Wall "$ROOT_DIR/src/minicobc.cob" -o "$ROOT_DIR/build/bin/minicobc"

"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/board.cob" "$BUILD_DIR/board.c"
"$ROOT_DIR/build/bin/minicobc" "$CHESS_DIR/src/fen.cob" "$BUILD_DIR/fen.c"

gcc -std=c11 -c "$BUILD_DIR/board.c" -o "$BUILD_DIR/board.o"
gcc -std=c11 -c "$BUILD_DIR/fen.c" -o "$BUILD_DIR/fen.o"
gcc -std=c11 "$ROOT_DIR/tests/chess/phase1_fen_harness.c" \
    "$BUILD_DIR/board.o" "$BUILD_DIR/fen.o" \
    -o "$BUILD_DIR/minicobc-phase1"

"$BUILD_DIR/minicobc-phase1" > "$BUILD_DIR/minicobc.out"

cobc -x -free \
    -I "$CHESS_DIR" \
    "$ROOT_DIR/tests/chess/phase1_fen_ref.cob" \
    "$CHESS_DIR/src/board.cob" \
    "$CHESS_DIR/src/fen.cob" \
    -o "$BUILD_DIR/gnucobol-phase1"

"$BUILD_DIR/gnucobol-phase1" > "$BUILD_DIR/gnucobol.out"
perl -pe 'if (/^([A-Z0-9]+)\s+(.*)$/) { $label=$1; $rest=$2; $rest =~ s/ //g; $_="$label $rest\n"; }' \
    "$BUILD_DIR/gnucobol.out" > "$BUILD_DIR/gnucobol.norm"
perl -pe 'if (/^([A-Z0-9]+)\s+(.*)$/) { $label=$1; $rest=$2; $rest =~ s/ //g; $_="$label $rest\n"; }' \
    "$BUILD_DIR/minicobc.out" > "$BUILD_DIR/minicobc.norm"
diff -u "$BUILD_DIR/gnucobol.norm" "$BUILD_DIR/minicobc.norm"
echo "phase1 chess BOARD+FEN generic build matched GnuCOBOL"
