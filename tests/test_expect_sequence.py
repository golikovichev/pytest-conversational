"""Tests for the said_in_order sequence matcher."""

from __future__ import annotations

import pytest

from pytest_conversational import expect
from pytest_conversational.conversation import Conversation, Turn


def _convo(*bot_replies: str) -> Conversation:
    """Build a conversation whose bot said each reply, one per turn."""
    return Conversation(turns=[Turn(user="_", bot=reply) for reply in bot_replies])


class TestSaidInOrder:
    def test_phrases_in_order_across_replies_passes(self) -> None:
        convo = _convo("What is your name?", "Where to?", "Confirmed, thanks.")
        expect.said_in_order(convo, ["name", "where to", "confirmed"])

    def test_multiple_phrases_in_one_reply_in_order_passes(self) -> None:
        convo = _convo("First I ask your name, then your destination.")
        expect.said_in_order(convo, ["name", "destination"])

    def test_out_of_order_raises_naming_failing_phrase(self) -> None:
        # Bot asked name first, then destination. Asserting the reverse order
        # must fail on the phrase that appears too early to satisfy the order.
        convo = _convo("What is your name?", "Where to?")
        with pytest.raises(AssertionError, match="'name'"):
            expect.said_in_order(convo, ["where to", "name"])

    def test_missing_phrase_raises(self) -> None:
        convo = _convo("Hello", "Goodbye")
        with pytest.raises(AssertionError, match="'confirmed'"):
            expect.said_in_order(convo, ["hello", "confirmed"])

    def test_case_insensitive_by_default(self) -> None:
        convo = _convo("ASKING NAME", "asking DESTINATION")
        expect.said_in_order(convo, ["name", "destination"])

    def test_case_sensitive_mode_enforces_case(self) -> None:
        convo = _convo("asking Name")
        expect.said_in_order(convo, ["Name"], case_sensitive=True)
        with pytest.raises(AssertionError):
            expect.said_in_order(convo, ["name"], case_sensitive=True)

    def test_empty_phrases_raises_valueerror(self) -> None:
        convo = _convo("anything")
        with pytest.raises(ValueError, match="at least one"):
            expect.said_in_order(convo, [])

    def test_empty_string_phrase_raises_valueerror(self) -> None:
        # An empty phrase would "match" at the cursor without advancing it,
        # silently checking nothing. Reject it like an empty list.
        convo = _convo("hello")
        with pytest.raises(ValueError, match="non-empty"):
            expect.said_in_order(convo, ["hello", ""])

    def test_none_convo_raises(self) -> None:
        with pytest.raises(AssertionError, match="None"):
            expect.said_in_order(None, ["hi"])  # type: ignore[arg-type]

    def test_no_turns_raises(self) -> None:
        with pytest.raises(AssertionError, match="'hi'"):
            expect.said_in_order(Conversation(), ["hi"])

    def test_failure_message_shows_transcript(self) -> None:
        convo = _convo("Hello there", "Goodbye now")
        try:
            expect.said_in_order(convo, ["hello", "confirmed"])
        except AssertionError as e:
            assert "confirmed" in str(e)
            assert "Goodbye now" in str(e)
        else:
            pytest.fail("expected AssertionError")

    def test_non_str_phrase_raises_typeerror(self) -> None:
        convo = _convo("hello")
        with pytest.raises(TypeError):
            expect.said_in_order(convo, [42])  # type: ignore[list-item]

    def test_none_bot_reply_treated_as_empty_not_crash(self) -> None:
        # A partial/failed turn can leave turn.bot unset. Such a reply must
        # contribute no match rather than raise AttributeError.
        convo = Conversation(
            turns=[Turn(user="_", bot=None), Turn(user="_", bot="confirmed")]  # type: ignore[arg-type]
        )
        expect.said_in_order(convo, ["confirmed"])
        with pytest.raises(AssertionError, match="'missing'"):
            expect.said_in_order(convo, ["confirmed", "missing"])

    def test_same_reply_reused_when_non_overlapping(self) -> None:
        # A later phrase may match the same reply as an earlier one, as long as
        # it starts after the earlier phrase ends.
        convo = _convo("name then destination")
        expect.said_in_order(convo, ["name", "then", "destination"])

    def test_overlapping_phrases_fail_non_overlapping(self) -> None:
        # Matches are non-overlapping: "ello" starts inside "hello", so once
        # "hello" is consumed there is no later occurrence of "ello".
        convo = _convo("hello world")
        with pytest.raises(AssertionError, match="'ello'"):
            expect.said_in_order(convo, ["hello", "ello"])
