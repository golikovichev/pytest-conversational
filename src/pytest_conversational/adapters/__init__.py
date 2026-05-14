"""Built-in bot adapters.

The HTTP webhook adapter depends on the optional ``[http]`` extra
(``httpx``). The base install must not fail when ``httpx`` is missing,
so the import is wrapped: when ``httpx`` is unavailable, a stub
``http_webhook`` callable replaces the real adapter and raises a
helpful ImportError only when the user actually tries to use it.
"""

from __future__ import annotations

__all__ = ["http_webhook"]

try:
    from pytest_conversational.adapters.http_webhook import (
        http_webhook as http_webhook,
    )
except ImportError as _http_webhook_import_error:
    _error = _http_webhook_import_error

    def http_webhook(*args, **kwargs):
        raise ImportError(
            "http_webhook requires the optional 'httpx' dependency. "
            "Install with: pip install pytest-conversational[http]"
        ) from _error
