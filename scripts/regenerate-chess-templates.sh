#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="${1:-$ROOT_DIR/external/agentic-chessengine-cobol-codex}"
OUT_DIR="$ROOT_DIR/templates/compat/chess"
EXPECTED_COMMIT="faf0f163e9b2b4b6475262fc8f00fcaeeedf4919"

if [[ ! -d "$REPO_DIR/src" || ! -d "$REPO_DIR/copybooks" ]]; then
    echo "missing chess engine repo: $REPO_DIR" >&2
    exit 1
fi

if git -C "$REPO_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
    CURRENT_COMMIT="$(git -C "$REPO_DIR" rev-parse HEAD)"
    if [[ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]]; then
        echo "warning: expected $EXPECTED_COMMIT but found $CURRENT_COMMIT" >&2
    fi
fi

mkdir -p "$OUT_DIR"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/minicob-chessXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

cp "$REPO_DIR"/src/*.cob "$tmpdir"/
mkdir -p "$tmpdir/copybooks"
cp "$REPO_DIR"/copybooks/*.cpy "$tmpdir"/copybooks/

(
    cd "$tmpdir"
    cobc -C -free -frecursive -Wall *.cob

    cat >> main.c <<'EOF'

int
main (int argc, char **argv)
{
  int rc;

  cob_init (argc, argv);
  rc = COBOCHESS ();
  cob_tidy ();
  return rc;
}
EOF

    for generated in \
        main.c main.c.h main.c.l.h \
        board.c board.c.h board.c.l.h \
        fen.c fen.c.h fen.c.l.h \
        attack.c attack.c.h attack.c.l.h \
        movegen.c movegen.c.h movegen.c.l.h \
        makemove.c makemove.c.h makemove.c.l1.h makemove.c.l2.h \
        perft.c perft.c.h perft.c.l.h \
        time.c time.c.h time.c.l.h \
        eval.c eval.c.h eval.c.l.h \
        search.c search.c.h search.c.l1.h search.c.l2.h search.c.l3.h \
        uci.c uci.c.h uci.c.l.h; do
        perl -pe 's/\t/    /g' "$generated" > "$OUT_DIR/$generated"
    done
)

echo "wrote $OUT_DIR"
