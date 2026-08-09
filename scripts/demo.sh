#!/usr/bin/env bash
# AuditLens — deterministic bias & data-quality audit demo.
#
# Runs FULLY OFFLINE: no network, no API keys, no LLM. Uses the `auditlens`
# CLI against the bundled example CSV; the findings table is deterministic and
# the markdown/HTML/JSON report artifacts land in demo-output/.
#
# Usage:
#   ./scripts/demo.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDITLENS="$ROOT_DIR/.venv/bin/auditlens"
EXAMPLE_CSV="$ROOT_DIR/examples/quickstart.csv"
OUT_DIR="$ROOT_DIR/demo-output"

if [[ ! -x "$AUDITLENS" ]]; then
  echo "Missing auditlens CLI at .venv/bin/auditlens" >&2
  echo "Set it up once with:" >&2
  echo "  python3 -m venv $ROOT_DIR/.venv" >&2
  echo "  $ROOT_DIR/.venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if [[ ! -f "$EXAMPLE_CSV" ]]; then
  echo "Missing example dataset: $EXAMPLE_CSV" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

"$AUDITLENS" audit "$EXAMPLE_CSV" --sensitive group sex --target target
echo
"$AUDITLENS" report "$EXAMPLE_CSV" --sensitive group sex --target target -o "$OUT_DIR"
echo
echo "Artifacts:"
ls -la "$OUT_DIR"
echo
echo "Next steps:"
echo "  - Use it in your own notebook:  from auditlens import audit"
echo "  - Enable Layer 2 LLM interpretation: pass task_description=..."
echo "  - Compare with the committed example: docs/examples/quickstart-result.md"
