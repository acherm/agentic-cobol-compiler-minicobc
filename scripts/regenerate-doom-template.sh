#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${1:-$ROOT_DIR/external/agentic-cobol-doom}"
OUT_DIR="$ROOT_DIR/templates/compat/doom"
EXPECTED_COMMIT="18ce52b3f7dd4d6d229d4a743513c39960959b44"

if [[ ! -f "$REPO_DIR/doom.cob" || ! -f "$REPO_DIR/terminal-io.c" ]]; then
    echo "missing COBOL-DOOM repo: $REPO_DIR" >&2
    exit 1
fi

if git -C "$REPO_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
    CURRENT_COMMIT="$(git -C "$REPO_DIR" rev-parse HEAD)"
    if [[ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]]; then
        echo "warning: expected $EXPECTED_COMMIT but found $CURRENT_COMMIT" >&2
    fi
fi

mkdir -p "$OUT_DIR"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/minicob-doomXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

cp "$REPO_DIR/doom.cob" "$tmpdir/"

(
    cd "$tmpdir"
    cobc -C -free doom.cob

    cat >> doom.c <<'EOF'

int
main (int argc, char **argv)
{
  int rc;

  cob_init (argc, argv);
  rc = COBOL__DOOM ();
  cob_tidy ();
  return rc;
}
EOF

    for generated in doom.c doom.c.h doom.c.l.h; do
        perl -pe 's/\t/    /g' "$generated" > "$OUT_DIR/$generated"
    done
)

echo "wrote $OUT_DIR"
