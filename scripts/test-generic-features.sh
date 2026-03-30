#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build/bin build/generated build/out build/helpers

cobc -x -free src/minicobc.cob -o build/bin/minicobc

./build/bin/minicobc examples/generic/paragraphs.cob build/generated/paragraphs.c
gcc -std=c99 -O2 build/generated/paragraphs.c -o build/bin/paragraphs
./build/bin/paragraphs > build/out/paragraphs.txt
diff -u expected/generic/paragraphs.txt build/out/paragraphs.txt

./build/bin/minicobc examples/generic/call_value.cob build/generated/call_value.c
gcc -std=c99 -O2 build/generated/call_value.c examples/generic/call_helpers.c -o build/bin/call_value
./build/bin/call_value > build/out/call_value.txt
diff -u expected/generic/call_value.txt build/out/call_value.txt

./build/bin/minicobc examples/generic/call_ref.cob build/generated/call_ref.c
gcc -std=c99 -O2 build/generated/call_ref.c examples/generic/call_helpers.c -o build/bin/call_ref
./build/bin/call_ref > build/out/call_ref.txt
diff -u expected/generic/call_ref.txt build/out/call_ref.txt

./build/bin/minicobc examples/generic/call_indexed_value.cob build/generated/call_indexed_value.c
gcc -std=c99 -O2 build/generated/call_indexed_value.c examples/generic/call_helpers.c -o build/bin/call_indexed_value
./build/bin/call_indexed_value > build/out/call_indexed_value.txt
diff -u expected/generic/call_indexed_value.txt build/out/call_indexed_value.txt

./build/bin/minicobc examples/generic/call_alpha_ref.cob build/generated/call_alpha_ref.c
gcc -std=c99 -O2 build/generated/call_alpha_ref.c examples/generic/call_helpers.c -o build/bin/call_alpha_ref
./build/bin/call_alpha_ref > build/out/call_alpha_ref.txt
diff -u expected/generic/call_alpha_ref.txt build/out/call_alpha_ref.txt

./build/bin/minicobc examples/generic/multiline_call.cob build/generated/multiline_call.c
gcc -std=c99 -O2 build/generated/multiline_call.c examples/generic/call_helpers.c -o build/bin/multiline_call
./build/bin/multiline_call > build/out/multiline_call.txt
diff -u expected/generic/multiline_call.txt build/out/multiline_call.txt

./build/bin/minicobc examples/generic/multiline_compute.cob build/generated/multiline_compute.c
gcc -std=c99 -O2 build/generated/multiline_compute.c -o build/bin/multiline_compute
./build/bin/multiline_compute > build/out/multiline_compute.txt
diff -u expected/generic/multiline_compute.txt build/out/multiline_compute.txt

./build/bin/minicobc examples/generic/multiline_if.cob build/generated/multiline_if.c
gcc -std=c99 -O2 build/generated/multiline_if.c -o build/bin/multiline_if
./build/bin/multiline_if > build/out/multiline_if.txt
diff -u expected/generic/multiline_if.txt build/out/multiline_if.txt

./build/bin/minicobc examples/generic/evaluate_value.cob build/generated/evaluate_value.c
gcc -std=c99 -O2 build/generated/evaluate_value.c -o build/bin/evaluate_value
./build/bin/evaluate_value > build/out/evaluate_value.txt
diff -u expected/generic/evaluate_value.txt build/out/evaluate_value.txt

./build/bin/minicobc examples/generic/evaluate_true.cob build/generated/evaluate_true.c
gcc -std=c99 -O2 build/generated/evaluate_true.c -o build/bin/evaluate_true
./build/bin/evaluate_true > build/out/evaluate_true.txt
diff -u expected/generic/evaluate_true.txt build/out/evaluate_true.txt

./build/bin/minicobc examples/generic/evaluate_inline.cob build/generated/evaluate_inline.c
gcc -std=c99 -O2 build/generated/evaluate_inline.c -o build/bin/evaluate_inline
./build/bin/evaluate_inline > build/out/evaluate_inline.txt
diff -u expected/generic/evaluate_inline.txt build/out/evaluate_inline.txt

./build/bin/minicobc examples/generic/picx_move_display.cob build/generated/picx_move_display.c
gcc -std=c99 -O2 build/generated/picx_move_display.c -o build/bin/picx_move_display
./build/bin/picx_move_display > build/out/picx_move_display.txt
diff -u expected/generic/picx_move_display.txt build/out/picx_move_display.txt

./build/bin/minicobc examples/generic/occurs_numeric.cob build/generated/occurs_numeric.c
gcc -std=c99 -O2 build/generated/occurs_numeric.c -o build/bin/occurs_numeric
./build/bin/occurs_numeric > build/out/occurs_numeric.txt
diff -u expected/generic/occurs_numeric.txt build/out/occurs_numeric.txt

./build/bin/minicobc examples/generic/occurs_alpha.cob build/generated/occurs_alpha.c
gcc -std=c99 -O2 build/generated/occurs_alpha.c -o build/bin/occurs_alpha
./build/bin/occurs_alpha > build/out/occurs_alpha.txt
diff -u expected/generic/occurs_alpha.txt build/out/occurs_alpha.txt

./build/bin/minicobc examples/generic/group_fields.cob build/generated/group_fields.c
gcc -std=c99 -O2 build/generated/group_fields.c -o build/bin/group_fields
./build/bin/group_fields > build/out/group_fields.txt
diff -u expected/generic/group_fields.txt build/out/group_fields.txt

./build/bin/minicobc examples/generic/group_display.cob build/generated/group_display.c
gcc -std=c99 -O2 build/generated/group_display.c -o build/bin/group_display
./build/bin/group_display > build/out/group_display.txt
diff -u expected/generic/group_display.txt build/out/group_display.txt

./build/bin/minicobc examples/generic/group_accept.cob build/generated/group_accept.c
gcc -std=c99 -O2 build/generated/group_accept.c -o build/bin/group_accept
printf 'QWER0042\n' | ./build/bin/group_accept > build/out/group_accept.txt
diff -u expected/generic/group_accept.txt build/out/group_accept.txt

./build/bin/minicobc examples/generic/group_move.cob build/generated/group_move.c
gcc -std=c99 -O2 build/generated/group_move.c -o build/bin/group_move
./build/bin/group_move > build/out/group_move.txt
diff -u expected/generic/group_move.txt build/out/group_move.txt

./build/bin/minicobc examples/generic/group_move_packed.cob build/generated/group_move_packed.c
gcc -std=c99 -O2 build/generated/group_move_packed.c -o build/bin/group_move_packed
./build/bin/group_move_packed > build/out/group_move_packed.txt
diff -u expected/generic/group_move_packed.txt build/out/group_move_packed.txt

./build/bin/minicobc examples/generic/redefines_alias.cob build/generated/redefines_alias.c
gcc -std=c99 -O2 build/generated/redefines_alias.c -o build/bin/redefines_alias
./build/bin/redefines_alias > build/out/redefines_alias.txt
diff -u expected/generic/redefines_alias.txt build/out/redefines_alias.txt

./build/bin/minicobc examples/generic/redefines_text_view.cob build/generated/redefines_text_view.c
gcc -std=c99 -O2 build/generated/redefines_text_view.c -o build/bin/redefines_text_view
./build/bin/redefines_text_view > build/out/redefines_text_view.txt
diff -u expected/generic/redefines_text_view.txt build/out/redefines_text_view.txt

./build/bin/minicobc examples/generic/redefines_refmod.cob build/generated/redefines_refmod.c
gcc -std=c99 -O2 build/generated/redefines_refmod.c -o build/bin/redefines_refmod
./build/bin/redefines_refmod > build/out/redefines_refmod.txt
diff -u expected/generic/redefines_refmod.txt build/out/redefines_refmod.txt

./build/bin/minicobc examples/generic/redefines_numeric_view.cob build/generated/redefines_numeric_view.c
gcc -std=c99 -O2 build/generated/redefines_numeric_view.c -o build/bin/redefines_numeric_view
./build/bin/redefines_numeric_view > build/out/redefines_numeric_view.txt
diff -u expected/generic/redefines_numeric_view.txt build/out/redefines_numeric_view.txt

./build/bin/minicobc examples/generic/redefines_accept.cob build/generated/redefines_accept.c
gcc -std=c99 -O2 build/generated/redefines_accept.c -o build/bin/redefines_accept
printf 'QWER0042\n' | ./build/bin/redefines_accept > build/out/redefines_accept.txt
diff -u expected/generic/redefines_accept.txt build/out/redefines_accept.txt

./build/bin/minicobc examples/generic/group_redefines_group_move.cob build/generated/group_redefines_group_move.c
gcc -std=c99 -O2 build/generated/group_redefines_group_move.c -o build/bin/group_redefines_group_move
./build/bin/group_redefines_group_move > build/out/group_redefines_group_move.txt
diff -u expected/generic/group_redefines_group_move.txt build/out/group_redefines_group_move.txt

./build/bin/minicobc examples/generic/group_redefines_children.cob build/generated/group_redefines_children.c
gcc -std=c99 -O2 build/generated/group_redefines_children.c -o build/bin/group_redefines_children
./build/bin/group_redefines_children > build/out/group_redefines_children.txt
diff -u expected/generic/group_redefines_children.txt build/out/group_redefines_children.txt

./build/bin/minicobc examples/generic/group_occurs_children.cob build/generated/group_occurs_children.c
gcc -std=c99 -O2 build/generated/group_occurs_children.c -o build/bin/group_occurs_children
./build/bin/group_occurs_children > build/out/group_occurs_children.txt
diff -u expected/generic/group_occurs_children.txt build/out/group_occurs_children.txt

./build/bin/minicobc examples/generic/group_occurs_accept.cob build/generated/group_occurs_accept.c
gcc -std=c99 -O2 build/generated/group_occurs_accept.c -o build/bin/group_occurs_accept
printf 'QWER0042\n' | ./build/bin/group_occurs_accept > build/out/group_occurs_accept.txt
diff -u expected/generic/group_occurs_accept.txt build/out/group_occurs_accept.txt

./build/bin/minicobc examples/generic/group_occurs_value.cob build/generated/group_occurs_value.c
gcc -std=c99 -O2 build/generated/group_occurs_value.c -o build/bin/group_occurs_value
./build/bin/group_occurs_value > build/out/group_occurs_value.txt
diff -u expected/generic/group_occurs_value.txt build/out/group_occurs_value.txt

./build/bin/minicobc examples/generic/signed_comp5.cob build/generated/signed_comp5.c
gcc -std=c99 -O2 build/generated/signed_comp5.c -o build/bin/signed_comp5
./build/bin/signed_comp5 > build/out/signed_comp5.txt
diff -u expected/generic/signed_comp5.txt build/out/signed_comp5.txt

./build/bin/minicobc examples/generic/perform_paragraph_until.cob build/generated/perform_paragraph_until.c
gcc -std=c99 -O2 build/generated/perform_paragraph_until.c -o build/bin/perform_paragraph_until
./build/bin/perform_paragraph_until > build/out/perform_paragraph_until.txt
diff -u expected/generic/perform_paragraph_until.txt build/out/perform_paragraph_until.txt

./build/bin/minicobc examples/generic/perform_varying.cob build/generated/perform_varying.c
gcc -std=c99 -O2 build/generated/perform_varying.c -o build/bin/perform_varying
./build/bin/perform_varying > build/out/perform_varying.txt
diff -u expected/generic/perform_varying.txt build/out/perform_varying.txt

./build/bin/minicobc examples/generic/compute_indexed_target.cob build/generated/compute_indexed_target.c
gcc -std=c99 -O2 build/generated/compute_indexed_target.c -o build/bin/compute_indexed_target
./build/bin/compute_indexed_target > build/out/compute_indexed_target.txt
diff -u expected/generic/compute_indexed_target.txt build/out/compute_indexed_target.txt

./build/bin/minicobc examples/generic/continue_stmt.cob build/generated/continue_stmt.c
gcc -std=c99 -O2 build/generated/continue_stmt.c -o build/bin/continue_stmt
./build/bin/continue_stmt > build/out/continue_stmt.txt
diff -u expected/generic/continue_stmt.txt build/out/continue_stmt.txt

./build/bin/minicobc examples/generic/picx_refmod.cob build/generated/picx_refmod.c
gcc -std=c99 -O2 build/generated/picx_refmod.c -o build/bin/picx_refmod
./build/bin/picx_refmod > build/out/picx_refmod.txt
diff -u expected/generic/picx_refmod.txt build/out/picx_refmod.txt

./build/bin/minicobc examples/generic/alpha_compare.cob build/generated/alpha_compare.c
gcc -std=c99 -O2 build/generated/alpha_compare.c -o build/bin/alpha_compare
./build/bin/alpha_compare > build/out/alpha_compare.txt
diff -u expected/generic/alpha_compare.txt build/out/alpha_compare.txt

./build/bin/minicobc examples/generic/function_sqrt.cob build/generated/function_sqrt.c
gcc -std=c99 -O2 build/generated/function_sqrt.c -o build/bin/function_sqrt
./build/bin/function_sqrt > build/out/function_sqrt.txt
diff -u expected/generic/function_sqrt.txt build/out/function_sqrt.txt

echo "generic paragraph, CALL, multiline, EVALUATE, storage-overlay, reference-modification, signed COMP-5, and paragraph UNTIL features matched expected output"
