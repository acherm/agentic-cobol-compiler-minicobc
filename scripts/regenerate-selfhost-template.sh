#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p templates/compat

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/minicob-selfXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

cobc -C -free src/minicobc.cob -o "$tmpdir/minicob-self.c"

awk -v header="$tmpdir/minicob-self.c.h" -v local_header="$tmpdir/minicob-self.c.l.h" '
    {
        if ($0 ~ /^#include ".*\.c\.h"$/) {
            while ((getline line < header) > 0) {
                gsub(/\t/, "    ", line)
                print line
            }
            close(header)
            next
        }
        if ($0 ~ /^  #include ".*\.c\.l\.h"$/ || $0 ~ /^#include ".*\.c\.l\.h"$/) {
            while ((getline line < local_header) > 0) {
                gsub(/\t/, "    ", line)
                print line
            }
            close(local_header)
            next
        }
        gsub(/\t/, "    ")
        print
    }
' "$tmpdir/minicob-self.c" > templates/compat/minicob.c

cat >> templates/compat/minicob.c <<'EOF'

int
main (int argc, char **argv)
{
  int rc;

  cob_init (argc, argv);
  rc = MINICOB ();
  cob_tidy ();
  return rc;
}
EOF

echo "wrote templates/compat/minicob.c"
