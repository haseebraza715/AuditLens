#!/usr/bin/env bash
# record.sh — regenerate assets/demo/ from scripts/demo/demo_body.sh.
#
# 1. Records the session with asciinema (real typing, real output).
# 2. Renders demo.mp4 (full demo) and demo.gif (12s preview) via the shared
#    mkdemo.sh pipeline (agg + ffmpeg).
#
# Usage:
#   ./scripts/demo/record.sh
#
# Requires: asciinema, agg, and the shared media venv (imageio-ffmpeg).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASSETS_DIR="$REPO_ROOT/assets/demo"
ASCIINEMA="${ASCIINEMA:-/Users/x/.local/bin/asciinema}"
MKDEMO="${MKDEMO:-/var/folders/bf/gc6myzc90cq_vrj0wd351wqw0000gn/T/opencode/media/mkdemo.sh}"

mkdir -p "$ASSETS_DIR"

echo "== recording session (asciinema)"
cd "$REPO_ROOT"
COLUMNS=100 LINES=30 TERM=xterm-256color script -q /dev/null bash -c \
  "stty cols 100 rows 30; exec $ASCIINEMA rec -q --overwrite '$ASSETS_DIR/demo.cast' -c 'bash scripts/demo/demo_body.sh'"

echo "== rendering mp4 + gif (mkdemo.sh)"
MEDIA_VENV="${MEDIA_VENV:-/var/folders/bf/gc6myzc90cq_vrj0wd351wqw0000gn/T/opencode/media/.venv}" "$MKDEMO" "$ASSETS_DIR/demo.cast" "$ASSETS_DIR"
