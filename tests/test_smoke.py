"""Smoke tests for the public API."""

from pytest_conversational import Conversation, Turn, __version__


def test_version_is_set():
    assert __version__ == "0.3.0"


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
