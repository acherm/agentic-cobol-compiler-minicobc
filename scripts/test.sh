#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/demo.sh > /dev/null
./scripts/test-gnucobol-core.sh > /dev/null
./scripts/test-generic-features.sh > /dev/null
./scripts/test-chess-phase1.sh > /dev/null
./scripts/test-chess-phase2.sh > /dev/null
./scripts/test-chess-phase3.sh > /dev/null
./scripts/test-chess-phase4.sh > /dev/null
./scripts/test-game15-generic.sh > /dev/null
./scripts/test-game15tree-generic.sh > /dev/null
./scripts/test-gameN-generic.sh > /dev/null

diff -u expected/primes.txt build/out/primes.txt
diff -u expected/collatz.txt build/out/collatz.txt
diff -u expected/gcd.txt build/out/gcd.txt
diff -u expected/generic/paragraphs.txt build/out/paragraphs.txt
diff -u expected/generic/call_value.txt build/out/call_value.txt
diff -u expected/generic/call_ref.txt build/out/call_ref.txt
diff -u expected/generic/multiline_call.txt build/out/multiline_call.txt
diff -u expected/generic/multiline_compute.txt build/out/multiline_compute.txt
diff -u expected/generic/multiline_if.txt build/out/multiline_if.txt
diff -u expected/generic/evaluate_value.txt build/out/evaluate_value.txt
diff -u expected/generic/evaluate_true.txt build/out/evaluate_true.txt
diff -u expected/generic/evaluate_inline.txt build/out/evaluate_inline.txt
diff -u expected/generic/picx_move_display.txt build/out/picx_move_display.txt
diff -u expected/generic/occurs_numeric.txt build/out/occurs_numeric.txt
diff -u expected/generic/occurs_alpha.txt build/out/occurs_alpha.txt
diff -u expected/generic/group_fields.txt build/out/group_fields.txt
diff -u expected/generic/group_display.txt build/out/group_display.txt
diff -u expected/generic/group_accept.txt build/out/group_accept.txt
diff -u expected/generic/group_move.txt build/out/group_move.txt
diff -u expected/generic/group_move_packed.txt build/out/group_move_packed.txt
diff -u expected/generic/redefines_alias.txt build/out/redefines_alias.txt
diff -u expected/generic/redefines_text_view.txt build/out/redefines_text_view.txt
diff -u expected/generic/redefines_numeric_view.txt build/out/redefines_numeric_view.txt
diff -u expected/generic/redefines_accept.txt build/out/redefines_accept.txt
diff -u expected/generic/multiline_move_alpha.txt build/out/multiline_move_alpha.txt
diff -u expected/generic/display_trim_trailing.txt build/out/display_trim_trailing.txt
diff -u expected/generic/move_numeric_to_picx.txt build/out/move_numeric_to_picx.txt
diff -u expected/generic/copybook_consts.txt build/out/copybook_consts.txt
diff -u expected/generic/entry_before_paragraph.txt build/out/entry_before_paragraph.txt

echo "minicobc and GnuCOBOL demonstrations matched expected output"
