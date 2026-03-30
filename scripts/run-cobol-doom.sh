#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${REPO_DIR:-external/agentic-cobol-doom}"
OUT_DIR="${OUT_DIR:-build/doom/generic}"

if [[ "${MINICOBC_VERBOSE:-0}" = "1" ]]; then
    ENGINE_PATH="$(./scripts/build-cobol-doom.sh "$REPO_DIR" "$OUT_DIR")"
else
    ENGINE_PATH="$(./scripts/build-cobol-doom.sh "$REPO_DIR" "$OUT_DIR" 2>/dev/null)"
fi

exec "$ENGINE_PATH" "$@"
