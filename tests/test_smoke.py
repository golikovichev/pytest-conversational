"""Smoke tests + first failing TDD test for Sess 3 work."""

import pytest

from pytest_conversational import Conversation, Turn, __version__


def test_version_is_set():
    assert __version__ == "0.1.0"


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


@pytest.mark.xfail(reason="Bot reply mechanism lands in Sess 3", strict=True)
def test_user_says_triggers_bot_reply():
    """Sess 3 will wire a bot adapter. Until then this fails by design."""
    convo = Conversation()
    convo.add_user("ping")
    assert convo.last is not None
    assert convo.last.bot == "pong"
