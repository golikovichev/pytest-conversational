"""pytest-conversational: rule-based multi-turn dialogue testing for pytest."""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

from pytest_conversational import allure_attachments, expect, scenarios
from pytest_conversational.allure_attachments import (
    attach_to_allure,
    render_transcript_markdown,
    serialize_transcript_json,
)
from pytest_conversational.conversation import (
    AsyncBotAdapter,
    BotAdapter,
    Conversation,
    Turn,
)
from pytest_conversational.scenarios import (
    Scenario,
    ScenarioLoadError,
    ScenarioTurn,
    load_scenarios,
    parametrize_scenarios,
)

try:
    __version__ = _pkg_version("pytest-conversational")
except PackageNotFoundError:
    # Package not installed (running from source tree without install).
    __version__ = "0.0.0+unknown"

__all__ = [
    "AsyncBotAdapter",
    "BotAdapter",
    "Conversation",
    "Scenario",
    "ScenarioLoadError",
    "ScenarioTurn",
    "Turn",
    "allure_attachments",
    "attach_to_allure",
    "expect",
    "load_scenarios",
    "parametrize_scenarios",
    "render_transcript_markdown",
    "scenarios",
    "serialize_transcript_json",
]
