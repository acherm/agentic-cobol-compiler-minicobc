#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CHESS_DIR="$ROOT_DIR/external/agentic-chessengine-cobol-codex"
BUILD_DIR="$ROOT_DIR/build/chess-phase4"
REF_BINARY="$CHESS_DIR/bin/cobochess"

mkdir -p "$BUILD_DIR"

"$ROOT_DIR/scripts/build-chess-engine.sh" "$CHESS_DIR" "$BUILD_DIR" > /dev/null
make -C "$CHESS_DIR" build > /dev/null

"$BUILD_DIR/cobochess" --perft-startpos 2 > "$BUILD_DIR/minicobc.out"
"$REF_BINARY" --perft-startpos 2 > "$BUILD_DIR/gnucobol.out"

diff -u "$BUILD_DIR/gnucobol.out" "$BUILD_DIR/minicobc.out"
echo "phase4 chess top-level generic build matched GnuCOBOL"
