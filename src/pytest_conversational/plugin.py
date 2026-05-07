"""pytest plugin entry. Provides the ``conversation`` fixture and a builder."""

from typing import Optional

import pytest

from pytest_conversational.conversation import BotAdapter, Conversation


@pytest.fixture
def conversation() -> Conversation:
    """Fresh empty Conversation, no adapter attached.

    Suitable for user-only flows or tests that pre-load turns by hand.
    For tests that need a bot, request ``conversation_factory`` instead.
    """
    return Conversation()


@pytest.fixture
def conversation_factory():
    """Factory that builds a Conversation with a chosen bot adapter.

    Example::

        def test_greeting(conversation_factory):
            convo = conversation_factory(bot=lambda text, c: "hi")
            convo.say("hello")
            assert convo.last.bot == "hi"
    """

    def _build(bot: Optional[BotAdapter] = None) -> Conversation:
        return Conversation(bot=bot)

    return _build
