#!/usr/bin/env bash
set -euo pipefail
set +m

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-pygame}"
OUT_DIR="${2:-build/pygame/compat}"
REF_DIR="${3:-build/pygame/gnucobol}"

if [[ ! -f "$REPO_DIR/examples/flappy.cob" || ! -f "$REPO_DIR/Makefile" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

MINI_EXE="$(./scripts/build-cobol-pygame.sh "$REPO_DIR" "$OUT_DIR" flappy)"

mkdir -p "$REF_DIR"
rm -f "$REF_DIR/flappy" "$REF_DIR/cpg.o"

cc $(sdl2-config --cflags) -c "$REPO_DIR/src/cpg.c" -o "$REF_DIR/cpg.o"
cobc -x -free -fstatic-call -I "$REPO_DIR/cobol" -o "$REF_DIR/flappy" \
    "$REPO_DIR/examples/flappy.cob" "$REF_DIR/cpg.o" $(sdl2-config --libs)
REF_EXE="$REF_DIR/flappy"

smoke_run() {
    local exe="$1"
    local label="$2"
    local out_file
    local err_file
    local pid
    local alive=0
    local rc

    out_file="$(mktemp "${TMPDIR:-/tmp}/pygame-smoke-outXXXX")"
    err_file="$(mktemp "${TMPDIR:-/tmp}/pygame-smoke-errXXXX")"

    SDL_VIDEODRIVER=dummy "$exe" >"$out_file" 2>"$err_file" &
    pid=$!
    sleep 1

    if kill -0 "$pid" 2>/dev/null; then
        alive=1
        kill -TERM "$pid" 2>/dev/null || true
    fi

    set +e
    wait "$pid"
    rc=$?
    set -e

    echo "$label: alive=$alive rc=$rc stdout=$(wc -c < "$out_file") stderr=$(wc -c < "$err_file")"

    rm -f "$out_file" "$err_file"

    if [[ "$alive" -ne 1 ]]; then
        return 1
    fi
}

smoke_run "$MINI_EXE" "minicobc"
smoke_run "$REF_EXE" "gnucobol"
