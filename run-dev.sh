#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing virtualenv python at .venv/bin/python"
  echo "Create it with:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  .venv/bin/python -m pip install -e '.[ui]'"
  exit 1
fi

missing_modules=()
"$VENV_PYTHON" -c "import streamlit" >/dev/null 2>&1 || missing_modules+=("streamlit")
"$VENV_PYTHON" -c "import dotenv" >/dev/null 2>&1 || missing_modules+=("python-dotenv")

if [[ ${#missing_modules[@]} -gt 0 ]]; then
  echo "Missing Python dependencies in .venv: ${missing_modules[*]}"
  echo "Install/update them with:"
  echo "  .venv/bin/python -m pip install -e '.[ui]'"
  exit 1
fi

cleanup() {
  echo ""
  echo "Stopping server and UI..."
  kill "${BACKEND_PID:-0}" "${FRONTEND_PID:-0}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Starting API server on http://127.0.0.1:8000 ..."
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  -u SOCKS_PROXY -u SOCKS5_PROXY -u socks_proxy -u socks5_proxy \
  "$VENV_PYTHON" -m uvicorn auditlens_server.app:app --reload --env-file "$ROOT_DIR/.env" &
BACKEND_PID=$!

echo "Starting Streamlit UI ..."
"$VENV_PYTHON" -m streamlit run "$ROOT_DIR/ui/auditlens_ui/app.py" \
  --server.headless true \
  --browser.gatherUsageStats false \
  --theme.base light \
  --theme.textColor "#102a43" \
  --theme.backgroundColor "#f6f9fc" \
  --theme.secondaryBackgroundColor "#ffffff" &
FRONTEND_PID=$!

echo "Server PID: $BACKEND_PID"
echo "UI PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both."

wait "$BACKEND_PID" "$FRONTEND_PID"
