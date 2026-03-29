#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build/bin build/generated build/out

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc

run_example() {
    local name="$1"
    local input_text="${2-}"
    local generated="build/generated/${name}.c"
    local binary="build/bin/${name}"
    local output="build/out/${name}.txt"

    rm -f "$generated" "$binary" "$output"
    ./build/bin/minicobc "examples/${name}.cob" "$generated"
    gcc -std=c11 "$generated" -o "$binary"

    if [[ -n "$input_text" ]]; then
        printf "%b" "$input_text" | "$binary" > "$output"
    else
        "$binary" > "$output"
    fi

    echo "== ${name} =="
    cat "$output"
    echo
}

run_example "primes"
run_example "collatz"
run_example "gcd" "1071\n462\n"
