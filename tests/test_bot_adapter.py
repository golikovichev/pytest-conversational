"""Bot adapter wiring: say() drives the adapter and records the reply."""

import pytest

from pytest_conversational import Conversation


def echo_bot(text: str, convo: Conversation) -> str:
    return f"echo: {text}"


def test_say_without_adapter_raises():
    convo = Conversation()
    with pytest.raises(RuntimeError, match="no bot adapter"):
        convo.say("hello")


def test_say_invokes_adapter_and_records_reply():
    convo = Conversation(bot=echo_bot)
    turn = convo.say("ping")
    assert turn.user == "ping"
    assert turn.bot == "echo: ping"
    assert convo.last is turn


def test_say_appends_in_order():
    convo = Conversation(bot=echo_bot)
    convo.say("one")
    convo.say("two")
    convo.say("three")
    assert [t.user for t in convo.turns] == ["one", "two", "three"]
    assert [t.bot for t in convo.turns] == ["echo: one", "echo: two", "echo: three"]


def test_history_returns_pairs():
    convo = Conversation(bot=echo_bot)
    convo.say("a")
    convo.say("b")
    assert convo.history == [("a", "echo: a"), ("b", "echo: b")]


def test_transcript_renders_dialogue():
    convo = Conversation(bot=echo_bot)
    convo.say("hi")
    convo.add_user("user-only line")
    text = convo.transcript()
    assert "USER: hi" in text
    assert "BOT:  echo: hi" in text
    assert "USER: user-only line" in text


def test_adapter_can_read_state_across_turns():
    """A real bot keeps a slot dict on convo.state and reads earlier turns."""

    def slot_filling_bot(text: str, convo: Conversation) -> str:
        slots = convo.state.setdefault("slots", {})
        if "name" not in slots:
            slots["name"] = text
            return "got it, what city?"
        if "city" not in slots:
            slots["city"] = text
            return f"hello {slots['name']} from {slots['city']}"
        return "done"

    convo = Conversation(bot=slot_filling_bot)
    convo.say("Mikhail")
    convo.say("Hove")
    assert convo.state["slots"] == {"name": "Mikhail", "city": "Hove"}
    assert convo.last.bot == "hello Mikhail from Hove"


def test_adapter_can_inspect_history_for_context():
    def parrot_last_user(text: str, convo: Conversation) -> str:
        if len(convo.turns) >= 2:
            previous_user = convo.turns[-2].user
            return f"you said {previous_user!r} before {text!r}"
        return "noted"

    convo = Conversation(bot=parrot_last_user)
    convo.say("first")
    convo.say("second")
    assert convo.last.bot == "you said 'first' before 'second'"


def test_factory_fixture_builds_with_adapter(pytester):
    pytester.makepyfile(
        """
        def test_with_factory(conversation_factory):
            convo = conversation_factory(bot=lambda t, c: "ok")
            convo.say("hi")
            assert convo.last.bot == "ok"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_factory_fixture_without_bot_still_works(pytester):
    pytester.makepyfile(
        """
        def test_no_bot(conversation_factory):
            convo = conversation_factory()
            convo.add_user("solo")
            assert convo.last.user == "solo"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


# M5: adapter exception propagates raw, partial turn stays visible (added 2026-05-20)


def test_adapter_exception_propagates_unchanged():
    """When the adapter raises, say() lets the original exception bubble.
    Callers can pattern-match on the concrete exception type."""

    def angry_bot(text: str, convo: Conversation) -> str:
        raise ValueError("upstream broke")

    convo = Conversation(bot=angry_bot)
    with pytest.raises(ValueError, match="upstream broke"):
        convo.say("hello")


def test_partial_turn_stays_in_history_on_adapter_failure():
    """A failed turn leaves user text in history with empty bot reply,
    so callers can inspect what was attempted before the failure."""

    def angry_bot(text: str, convo: Conversation) -> str:
        raise RuntimeError("nope")

    convo = Conversation(bot=angry_bot)
    with pytest.raises(RuntimeError):
        convo.say("attempt")
    assert len(convo.turns) == 1
    assert convo.turns[0].user == "attempt"
    assert convo.turns[0].bot == ""


def test_partial_turn_after_two_successful_turns():
    """Multi-turn conversation keeps successful turns intact and shows
    the failed third turn as user-only, no bot reply."""

    def bot(text: str, convo: Conversation) -> str:
        if text == "BOOM":
            raise IOError("network down")
        return f"ok {text}"

    convo = Conversation(bot=bot)
    convo.say("first")
    convo.say("second")
    with pytest.raises(IOError, match="network down"):
        convo.say("BOOM")
    assert len(convo.turns) == 3
    assert convo.turns[0].bot == "ok first"
    assert convo.turns[1].bot == "ok second"
    assert convo.turns[2].user == "BOOM"
    assert convo.turns[2].bot == ""
