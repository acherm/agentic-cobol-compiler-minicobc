#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-game15tictactoe}"

if [[ ! -d "$REPO_DIR" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p build/bin build/compat build/reference build/compat-check

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc

compile_with_minicobc() {
    local stem="$1"
    rm -f "build/compat/${stem}.c" "build/compat/${stem}"
    ./build/bin/minicobc "${REPO_DIR}/${stem}.cob" "build/compat/${stem}.c"
    gcc -std=c11 "build/compat/${stem}.c" -o "build/compat/${stem}"
}

compile_with_reference() {
    local stem="$1"
    cobc -x "${REPO_DIR}/${stem}.cob" -o "build/reference/${stem}"
}

run_case() {
    local label="$1"
    local stem="$2"
    shift 2

    "build/compat/${stem}" "$@" > "build/compat-check/${label}.mine.txt"
    "build/reference/${stem}" "$@" > "build/compat-check/${label}.ref.txt"
    diff -u \
        "build/compat-check/${label}.ref.txt" \
        "build/compat-check/${label}.mine.txt"
}

for stem in game15 game15tree game015 game015tree gameN; do
    compile_with_minicobc "$stem"
    compile_with_reference "$stem"
done

run_case game15_default game15
run_case game15_unique game15 --unique
run_case game15tree_depth2 game15tree --depth 2
run_case game015_default game015
run_case game015tree_depth2 game015tree --depth 2
run_case gameN_15_9 gameN 15 9
run_case gameN_12_8 gameN 12 8
run_case gameN_10 gameN 10

echo "all agentic-cobol-game15tictactoe checks matched GnuCOBOL"
