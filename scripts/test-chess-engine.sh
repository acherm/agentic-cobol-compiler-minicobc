#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-chessengine-cobol-codex}"
ENGINE_DIR="build/chess/generic"
OUT_DIR="build/chess/out"
REF_BINARY="$REPO_DIR/bin/cobochess"

if [[ ! -d "$REPO_DIR" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p build/bin "$ENGINE_DIR" "$OUT_DIR"

./scripts/build-chess-engine.sh "$REPO_DIR" "$ENGINE_DIR" > /dev/null

make -C "$REPO_DIR" build > /dev/null

run_cli_case() {
    local label="$1"
    shift

    "$ENGINE_DIR/cobochess" "$@" > "$OUT_DIR/$label.mine.txt"
    "$REF_BINARY" "$@" > "$OUT_DIR/$label.ref.txt"
    diff -u "$OUT_DIR/$label.ref.txt" "$OUT_DIR/$label.mine.txt"
}

run_stdin_case() {
    local label="$1"
    local input_text="$2"

    printf "%b" "$input_text" | "$ENGINE_DIR/cobochess" > "$OUT_DIR/$label.mine.txt"
    printf "%b" "$input_text" | "$REF_BINARY" > "$OUT_DIR/$label.ref.txt"
    diff -u "$OUT_DIR/$label.ref.txt" "$OUT_DIR/$label.mine.txt"
}

run_cli_case perft_startpos_2 --perft-startpos 2
run_cli_case perft_kiwipete_2 --perft "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1" 2
run_cli_case perft_ep_3 --perft "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1" 3
run_stdin_case uci_depth1 "uci\nisready\nposition startpos\ngo depth 1\nquit\n"

echo "generic chess engine checks matched GnuCOBOL"
