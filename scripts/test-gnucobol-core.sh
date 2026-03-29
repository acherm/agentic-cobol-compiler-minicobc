#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build/reference-core build/reference-out

run_reference() {
    local name="$1"
    local input_text="${2-}"
    local binary="build/reference-core/${name}"
    local output="build/reference-out/${name}.txt"

    rm -f "$binary" "$output"
    cobc -x -free "examples/${name}.cob" -o "$binary"

    if [[ -n "$input_text" ]]; then
        printf "%b" "$input_text" | "$binary" > "$output"
    else
        "$binary" > "$output"
    fi

    diff -u "expected/${name}.txt" "$output"
}

run_reference "primes"
run_reference "collatz"
run_reference "gcd" "1071\n462\n"

echo "gnucobol core demonstrations matched expected output"
