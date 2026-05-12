"""pytest-conversational: rule-based multi-turn dialogue testing for pytest."""

from pytest_conversational import expect
from pytest_conversational.conversation import BotAdapter, Conversation, Turn

__version__ = "0.3.0"
__all__ = ["BotAdapter", "Conversation", "Turn", "expect"]
