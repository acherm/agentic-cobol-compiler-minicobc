#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/demo.sh > /dev/null
./scripts/test-gnucobol-core.sh > /dev/null

diff -u expected/primes.txt build/out/primes.txt
diff -u expected/collatz.txt build/out/collatz.txt
diff -u expected/gcd.txt build/out/gcd.txt

echo "minicobc and GnuCOBOL demonstrations matched expected output"
