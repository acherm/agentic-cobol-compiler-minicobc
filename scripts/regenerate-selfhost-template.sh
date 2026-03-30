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

main_count="$(
awk '
    $0 == "main (int argc, char **argv)" {
        count++
    }
    END {
        print count + 0
    }
' templates/compat/minicob.c
)"

if [[ "$main_count" -gt 1 ]]; then
tmpfile="$(mktemp "${TMPDIR:-/tmp}/minicob-dedupeXXXX")"
awk '
    BEGIN {
        main_seen = 0
        pending_int = 0
        skip_main = 0
        brace_depth = 0
    }

    skip_main == 1 {
        if ($0 == "{") {
            brace_depth = 1
            next
        }
        if (brace_depth > 0) {
            if ($0 == "{") {
                brace_depth++
            } else if ($0 == "}") {
                brace_depth--
                if (brace_depth == 0) {
                    skip_main = 0
                }
            }
            next
        }
        next
    }

    pending_int == 1 {
        if ($0 == "main (int argc, char **argv)") {
            main_seen++
            if (main_seen == 1) {
                print pending_line
                print
            } else {
                skip_main = 1
            }
            pending_int = 0
            next
        }
        print pending_line
        pending_int = 0
    }

    {
        if ($0 == "int") {
            pending_int = 1
            pending_line = $0
            next
        }
        print
    }

    END {
        if (pending_int == 1) {
            print pending_line
        }
    }
' templates/compat/minicob.c > "$tmpfile"
mv "$tmpfile" templates/compat/minicob.c
main_count="$(
awk '
    $0 == "main (int argc, char **argv)" {
        count++
    }
    END {
        print count + 0
    }
' templates/compat/minicob.c
)"
fi

if [[ "$main_count" -eq 0 ]]; then
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
fi

echo "wrote templates/compat/minicob.c"
