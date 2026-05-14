"""Adapters module must import cleanly even when the optional ``httpx``
dependency is missing. The real ``http_webhook`` callable raises only
when the user actually invokes it.
"""

from __future__ import annotations

import importlib
import sys


def test_adapters_module_imports_without_eagerly_failing_on_httpx():
    """A user who installs pytest-conversational without ``[http]`` must
    still be able to `import pytest_conversational.adapters`. The base
    install ships no http_webhook scenarios, so any failure must surface
    on first call, not at import time."""
    # Force a fresh import to ensure the try/except path was exercised.
    for mod in list(sys.modules):
        if mod.startswith("pytest_conversational.adapters"):
            del sys.modules[mod]

    adapters = importlib.import_module("pytest_conversational.adapters")
    assert "http_webhook" in adapters.__all__
    assert callable(adapters.http_webhook)


def test_http_webhook_callable_exists_after_clean_reimport():
    """After fresh import, the attribute resolves to a callable (either
    the real adapter when httpx is installed, or the import-stub when
    httpx is missing). The caller must not have to guard on the
    attribute's existence."""
    for mod in list(sys.modules):
        if mod.startswith("pytest_conversational.adapters"):
            del sys.modules[mod]

    from pytest_conversational.adapters import http_webhook

    assert callable(http_webhook)
