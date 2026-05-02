"""pytest plugin entry point. Real fixtures land in Sess 3."""

import pytest

from pytest_conversational.conversation import Conversation


@pytest.fixture
def conversation() -> Conversation:
    """Empty Conversation, fresh per test."""
    return Conversation()
