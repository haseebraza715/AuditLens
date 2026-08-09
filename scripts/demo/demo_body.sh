#!/usr/bin/env bash
# demo_body.sh — drives the recorded demo session (deterministic, offline).
# Story: CSV in -> findings table with severities -> shareable report artifacts.
# Run from the repository root. Set PATH to the project venv so commands look clean.
# NOTE: edit this file to change the demo; then run scripts/demo/record.sh to regenerate.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PATH="$REPO_ROOT/.venv/bin:$PATH"

PROMPT='\033[1;32m❯\033[0m '
CHAR_DELAY=0.07

header() { printf '\033[1;36m%s\033[0m\n' "$1"; sleep 0.6; }
pause() { sleep "$1"; }

type_cmd() {
  printf "${PROMPT}"
  local cmd="$*"
  local i
  for ((i = 0; i < ${#cmd}; i++)); do
    printf '%s' "${cmd:$i:1}"
    sleep "$CHAR_DELAY"
  done
  printf '\n'
  sleep 0.4
}

run() {
  type_cmd "$@"
  "$@"
  sleep 1.2
}

header "AuditLens  -  deterministic bias & fairness audit (offline, no LLM)"
pause 0.8

header "Step 1: audit findings from the example CSV"
run auditlens audit examples/quickstart.csv --sensitive group sex --target target
pause 1.0

header "Step 2: write shareable report artifacts (markdown / HTML / JSON)"
run auditlens report examples/quickstart.csv --sensitive group sex --target target -o /tmp/auditlens-demo
pause 1.0

header "Step 3: inspect the artifacts"
run ls -la /tmp/auditlens-demo
pause 0.8
run head -n 10 /tmp/auditlens-demo/report.md

pause 1.0
header "Machine-readable output: same audit as JSON"
run auditlens audit examples/quickstart.csv --sensitive group sex --target target --format json

pause 1.5
header "Same CSV in -> same findings out.  Deterministic, byte-reproducible, zero API keys."
pause 2.5
