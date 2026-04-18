from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import APIRequestContext, Playwright, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _pythonpath_env() -> dict[str, str]:
    env = os.environ.copy()
    parts = [
        str(REPO_ROOT / "src"),
        str(REPO_ROOT / "server"),
        str(REPO_ROOT / "ui"),
    ]
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(parts + ([prev] if prev else []))
    return env


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    """Start uvicorn in a subprocess; tear down after the e2e session."""
    port = _pick_free_port()
    url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "auditlens_server.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        env=_pythonpath_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + 90.0
    last_exc: Exception | None = None
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"uvicorn exited early with code {proc.returncode}")
            try:
                r = httpx.get(f"{url}/health", timeout=1.0)
                if r.status_code == 200:
                    break
            except (httpx.HTTPError, OSError) as exc:
                last_exc = exc
                time.sleep(0.15)
        else:
            raise RuntimeError(f"server did not become ready at {url!r}") from last_exc

        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


@pytest.fixture(scope="session")
def playwright_request(live_server_url: str) -> Generator[APIRequestContext, None, None]:
    """Playwright HTTP client scoped to the live server (no browser)."""
    pw: Playwright | None = None
    ctx: APIRequestContext | None = None
    try:
        pw = sync_playwright().start()
        ctx = pw.request.new_context(base_url=live_server_url)
        yield ctx
    finally:
        if ctx is not None:
            ctx.dispose()
        if pw is not None:
            pw.stop()
