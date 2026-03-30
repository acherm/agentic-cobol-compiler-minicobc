#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-external/agentic-cobol-doom}"
OUT_DIR="build/doom/generic"

if [[ ! -f "$REPO_DIR/doom.cob" || ! -f "$REPO_DIR/terminal-io.c" ]]; then
    echo "missing repo: $REPO_DIR" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

./scripts/build-cobol-doom.sh "$REPO_DIR" "$OUT_DIR" > /dev/null
make -C "$REPO_DIR" doom > /dev/null

smoke_status() {
    python3 - "$1" <<'PY'
import subprocess
import sys
import time

path = sys.argv[1]
p = subprocess.Popen(
    [path],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(0.2)
alive = p.poll() is None
if alive:
    p.terminate()
    try:
        out, err = p.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
else:
    out, err = p.communicate()
print(
    f"alive={int(alive)} rc={p.returncode} "
    f"stdout={len(out)} stderr={len(err)}"
)
PY
}

MINE_STATUS="$(smoke_status "$OUT_DIR/cobol-doom")"
REF_STATUS="$(smoke_status "$REPO_DIR/doom")"

echo "minicobc: $MINE_STATUS"
echo "gnucobol: $REF_STATUS"

if [[ "$MINE_STATUS" != alive=1* ]]; then
    echo "generic minicobc-built COBOL-DOOM did not survive smoke startup" >&2
    exit 1
fi

if [[ "$REF_STATUS" != alive=1* ]]; then
    echo "GnuCOBOL-built COBOL-DOOM did not survive smoke startup" >&2
    exit 1
fi

echo "COBOL-DOOM generic build succeeded and passed smoke startup"
