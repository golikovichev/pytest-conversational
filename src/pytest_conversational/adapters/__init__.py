"""Built-in bot adapters. Optional, depend on extras (e.g. httpx for http_webhook)."""

from pytest_conversational.adapters.http_webhook import http_webhook

__all__ = ["http_webhook"]
