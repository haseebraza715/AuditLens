from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    """Skip e2e tests when Playwright is not installed (optional extra `[e2e]`)."""
    if "e2e" not in collection_path.parts:
        return None
    if importlib.util.find_spec("playwright") is None:
        return True
    return None
