#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build/bin build/generated build/selfhost/out

./scripts/regenerate-selfhost-template.sh > /dev/null

cobc -x -free -Wall src/minicobc.cob -o build/bin/minicobc
./build/bin/minicobc src/minicobc.cob build/generated/minicob-self.c
cc build/generated/minicob-self.c $(cob-config --cflags) $(cob-config --libs) -o build/bin/minicobc-self

./build/bin/minicobc-self src/minicobc.cob build/generated/minicob-self-stage2.c
diff -u build/generated/minicob-self.c build/generated/minicob-self-stage2.c

run_with_selfhost() {
    local name="$1"
    local input_text="${2-}"
    local generated="build/selfhost/${name}.c"
    local binary="build/selfhost/${name}"
    local output="build/selfhost/out/${name}.txt"

    rm -f "$generated" "$binary" "$output"
    ./build/bin/minicobc-self "examples/${name}.cob" "$generated"
    gcc -std=c11 "$generated" -o "$binary"

    if [[ -n "$input_text" ]]; then
        printf "%b" "$input_text" | "$binary" > "$output"
    else
        "$binary" > "$output"
    fi

    diff -u "expected/${name}.txt" "$output"
}

run_with_selfhost "primes"
run_with_selfhost "collatz"
run_with_selfhost "gcd" "1071\n462\n"

echo "self-hosted compiler matched expected outputs and reproduced its own C template"
