"""Tests for the import-time fallback branches in __init__ and adapters.

Two fallbacks are exercised here:

1. ``pytest_conversational.__version__`` reads from the installed package
   metadata, and falls back to a placeholder when the package is not
   installed (running from the source tree without ``pip install -e .``).

2. The HTTP webhook adapter is an optional extra. When ``httpx`` is
   missing, ``pytest_conversational.adapters.http_webhook`` must still
   import cleanly and only raise ``ImportError`` when a caller actually
   tries to use the adapter.

Both branches need ``importlib.reload`` to re-execute the module body
under the patched conditions, since the modules were already imported
by the time the test session started.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# ---------------------------------------------------------------------------
# __init__.py: PackageNotFoundError -> __version__ fallback
# ---------------------------------------------------------------------------


def test_version_falls_back_when_package_metadata_missing(monkeypatch):
    """If importlib.metadata cannot find the distribution, use a placeholder version."""
    import importlib.metadata

    def _raise_not_found(name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _raise_not_found)

    import pytest_conversational

    reloaded = importlib.reload(pytest_conversational)
    try:
        assert reloaded.__version__ == "0.0.0+unknown"
    finally:
        # Restore the real metadata reader so later tests see the true version.
        monkeypatch.undo()
        importlib.reload(pytest_conversational)


# ---------------------------------------------------------------------------
# adapters/__init__.py + adapters/http_webhook.py: missing httpx fallback
# ---------------------------------------------------------------------------


def _remove_modules(prefix: str) -> None:
    """Drop already-imported modules whose name starts with ``prefix`` from sys.modules."""
    for name in [
        m for m in list(sys.modules) if m == prefix or m.startswith(f"{prefix}.")
    ]:
        sys.modules.pop(name, None)


def test_http_webhook_adapter_raises_helpfully_when_httpx_missing(monkeypatch):
    """Without httpx installed, the package must still import. The adapter
    becomes a stub that raises ImportError with install instructions only
    when the user actually calls it.
    """
    # Force the import of httpx (and the http_webhook submodule that depends
    # on it) to fail. The adapters package wraps the inner import in
    # try/except and substitutes a stub callable on failure.
    monkeypatch.setitem(sys.modules, "httpx", None)
    _remove_modules("pytest_conversational.adapters")

    adapters = importlib.import_module("pytest_conversational.adapters")
    try:
        assert callable(adapters.http_webhook)
        with pytest.raises(
            ImportError, match=r"http_webhook requires the optional 'httpx'"
        ):
            adapters.http_webhook("anything")
    finally:
        # Clean up: drop the broken modules and restore the real adapters
        # package so unrelated tests in the same session see httpx again.
        monkeypatch.undo()
        _remove_modules("pytest_conversational.adapters")
        importlib.import_module("pytest_conversational.adapters")


def test_http_webhook_module_raises_on_direct_import_without_httpx(monkeypatch):
    """Importing ``pytest_conversational.adapters.http_webhook`` directly,
    without httpx, raises ImportError pointing at the optional extra.
    """
    monkeypatch.setitem(sys.modules, "httpx", None)
    _remove_modules("pytest_conversational.adapters")

    try:
        with pytest.raises(ImportError, match=r"http_webhook requires httpx"):
            importlib.import_module("pytest_conversational.adapters.http_webhook")
    finally:
        monkeypatch.undo()
        _remove_modules("pytest_conversational.adapters")
        importlib.import_module("pytest_conversational.adapters")
