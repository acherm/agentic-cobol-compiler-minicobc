#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_BIN="${MINICOBC_CHESS_BIN:-$ROOT_DIR/build/chess/generic/cobochess}"

exec /opt/homebrew/bin/stdbuf -oL "$ENGINE_BIN"
