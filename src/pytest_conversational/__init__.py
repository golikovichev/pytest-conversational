"""pytest-conversational: rule-based multi-turn dialogue testing for pytest."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from pytest_conversational import allure_attachments, expect
from pytest_conversational.allure_attachments import (
    attach_to_allure,
    render_transcript_markdown,
    serialize_transcript_json,
)
from pytest_conversational.conversation import BotAdapter, Conversation, Turn

try:
    __version__ = _pkg_version("pytest-conversational")
except PackageNotFoundError:
    # Package not installed (running from source tree without install).
    __version__ = "0.0.0+unknown"

__all__ = [
    "BotAdapter",
    "Conversation",
    "Turn",
    "allure_attachments",
    "attach_to_allure",
    "expect",
    "render_transcript_markdown",
    "serialize_transcript_json",
]
