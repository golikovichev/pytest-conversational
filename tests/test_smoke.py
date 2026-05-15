"""Smoke tests for the public API."""

import re

from pytest_conversational import Conversation, Turn, __version__


def test_version_is_set():
    # Version is read from package metadata via importlib.metadata.
    # In a stale dev install it may lag pyproject.toml, so accept any
    # non-empty PEP 440 style string.
    assert isinstance(__version__, str)
    assert __version__
    assert re.match(r"^\d+\.\d+", __version__) or __version__.startswith("0.0.0+")


def test_empty_conversation_has_no_turns():
    convo = Conversation()
    assert convo.turns == []
    assert convo.last is None


def test_add_user_appends_turn():
    convo = Conversation()
    turn = convo.add_user("hello")
    assert turn.user == "hello"
    assert turn.bot == ""
    assert convo.last is turn
    assert len(convo.turns) == 1


def test_turn_metadata_isolated_per_instance():
    a = Turn(user="hi")
    b = Turn(user="hi")
    a.metadata["intent"] = "greet"
    assert b.metadata == {}


def test_fixture_provides_empty_conversation(pytester):
    pytester.makepyfile(
        """
        def test_smoke(conversation):
            assert conversation.turns == []
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
