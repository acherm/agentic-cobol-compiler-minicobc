#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${1:-$ROOT_DIR/external/agentic-cobol-pygame}"
OUT_DIR="$ROOT_DIR/templates/compat/pygame"
EXPECTED_COMMIT="b2095a1ce046cb654bff9e072c96e1ce4d2b11d9"

if [[ ! -f "$REPO_DIR/examples/flappy.cob" || ! -f "$REPO_DIR/cobol/cpg.cpy" ]]; then
    echo "missing pygame repo: $REPO_DIR" >&2
    exit 1
fi

if git -C "$REPO_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
    CURRENT_COMMIT="$(git -C "$REPO_DIR" rev-parse HEAD)"
    if [[ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]]; then
        echo "warning: expected $EXPECTED_COMMIT but found $CURRENT_COMMIT" >&2
    fi
fi

mkdir -p "$OUT_DIR"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/minicob-pygameXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

mkdir -p "$tmpdir/cobol"
cp "$REPO_DIR/examples/flappy.cob" "$tmpdir/"
cp "$REPO_DIR/cobol/cpg.cpy" "$tmpdir/cobol/"

(
    cd "$tmpdir"
    cobc -C -x -free -fstatic-call -I cobol -o flappy.c flappy.cob

    for generated in flappy.c flappy.c.h flappy.c.l.h; do
        perl -pe 's/\t/    /g' "$generated" > "$OUT_DIR/$generated"
    done
)

echo "wrote $OUT_DIR"
