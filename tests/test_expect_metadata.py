"""Tests for the slot / state / intent / latency matchers (Sess 6 scope).

These four matchers inspect adapter-recorded metadata rather than the
bot's text reply. Each test exercises both the happy path and the
expected AssertionError when metadata is missing or mismatched.
"""

from __future__ import annotations

import pytest

from pytest_conversational import expect
from pytest_conversational.conversation import Conversation, Turn


# ---------------------------------------------------------------------------
# has_intent
# ---------------------------------------------------------------------------


def test_has_intent_pass_when_metadata_matches():
    turn = Turn(
        user="when does my order arrive",
        bot="checking",
        metadata={"intent": "order_status"},
    )
    expect.has_intent(turn, "order_status")


def test_has_intent_fails_when_intent_differs():
    turn = Turn(user="hi", bot="hello", metadata={"intent": "greeting"})
    with pytest.raises(
        AssertionError, match=r"expected intent 'order_status', got 'greeting'"
    ):
        expect.has_intent(turn, "order_status")


def test_has_intent_fails_when_no_intent_key():
    turn = Turn(user="hi", bot="hello", metadata={})
    with pytest.raises(AssertionError, match=r"no 'intent' key"):
        expect.has_intent(turn, "greeting")


def test_has_intent_fails_on_none_turn():
    with pytest.raises(AssertionError, match=r"None turn"):
        expect.has_intent(None, "anything")


# ---------------------------------------------------------------------------
# has_slot
# ---------------------------------------------------------------------------


def test_has_slot_pass_when_slot_present_no_value_check():
    turn = Turn(
        user="to Brighton", bot="ok", metadata={"slots": {"destination": "Brighton"}}
    )
    expect.has_slot(turn, "destination")


def test_has_slot_pass_when_value_matches():
    turn = Turn(
        user="to Brighton", bot="ok", metadata={"slots": {"destination": "Brighton"}}
    )
    expect.has_slot(turn, "destination", value="Brighton")


def test_has_slot_fails_when_value_differs():
    turn = Turn(
        user="to London", bot="ok", metadata={"slots": {"destination": "London"}}
    )
    with pytest.raises(
        AssertionError, match=r"expected slot 'destination'='Brighton', got 'London'"
    ):
        expect.has_slot(turn, "destination", value="Brighton")


def test_has_slot_fails_when_slot_absent():
    turn = Turn(user="hi", bot="hello", metadata={"slots": {"greeting": "hi"}})
    with pytest.raises(AssertionError, match=r"slot is unset"):
        expect.has_slot(turn, "destination")


def test_has_slot_fails_when_no_slots_dict():
    turn = Turn(user="hi", bot="hello", metadata={})
    with pytest.raises(AssertionError, match=r"no 'slots' dict"):
        expect.has_slot(turn, "destination")


def test_has_slot_fails_when_slots_is_not_a_dict():
    """If the adapter recorded slots as a string or list by mistake, fail loudly."""
    turn = Turn(user="hi", bot="hello", metadata={"slots": "destination=Brighton"})
    with pytest.raises(AssertionError, match=r"no 'slots' dict"):
        expect.has_slot(turn, "destination")


def test_has_slot_fails_on_none_turn():
    """Calling the matcher with a None turn must raise instead of crashing on attribute access."""
    with pytest.raises(AssertionError, match=r"None turn"):
        expect.has_slot(None, "destination")


def test_has_slot_accepts_none_value_explicit():
    """If adapter records slot=None explicitly, has_slot(value=None) should pass."""
    turn = Turn(user="cancel", bot="ok", metadata={"slots": {"destination": None}})
    expect.has_slot(turn, "destination", value=None)


# ---------------------------------------------------------------------------
# has_state
# ---------------------------------------------------------------------------


def test_has_state_pass_when_key_present():
    convo = Conversation(state={"phase": "post_status_inquiry"})
    expect.has_state(convo, "phase")


def test_has_state_pass_when_value_matches():
    convo = Conversation(state={"phase": "post_status_inquiry"})
    expect.has_state(convo, "phase", value="post_status_inquiry")


def test_has_state_fails_when_value_differs():
    convo = Conversation(state={"phase": "greeting"})
    with pytest.raises(
        AssertionError, match=r"expected state 'phase'='checkout', got 'greeting'"
    ):
        expect.has_state(convo, "phase", value="checkout")


def test_has_state_fails_when_key_absent():
    convo = Conversation(state={})
    with pytest.raises(AssertionError, match=r"key is unset"):
        expect.has_state(convo, "phase")


def test_has_state_fails_on_none_conversation():
    with pytest.raises(AssertionError, match=r"None conversation"):
        expect.has_state(None, "phase")


def test_has_state_fails_when_state_is_not_a_dict():
    """A custom convo-like object that exposes ``state`` as the wrong type must fail loudly."""
    from types import SimpleNamespace

    fake_convo = SimpleNamespace(state="phase=greeting")
    with pytest.raises(AssertionError, match=r"no 'state' dict"):
        expect.has_state(fake_convo, "phase")


# ---------------------------------------------------------------------------
# responds_within
# ---------------------------------------------------------------------------


def test_responds_within_pass_when_under_budget():
    turn = Turn(user="hi", bot="hello", metadata={"latency_ms": 120})
    expect.responds_within(turn, 0.5)


def test_responds_within_pass_at_exact_budget():
    turn = Turn(user="hi", bot="hello", metadata={"latency_ms": 500})
    expect.responds_within(turn, 0.5)


def test_responds_within_fails_over_budget():
    turn = Turn(user="hi", bot="hello", metadata={"latency_ms": 600})
    with pytest.raises(AssertionError, match=r"got 600ms"):
        expect.responds_within(turn, 0.5)


def test_responds_within_fails_no_latency_key():
    turn = Turn(user="hi", bot="hello", metadata={})
    with pytest.raises(AssertionError, match=r"no 'latency_ms' key"):
        expect.responds_within(turn, 1.0)


def test_responds_within_fails_on_none_turn():
    """Calling the matcher with a None turn must raise instead of crashing on attribute access."""
    with pytest.raises(AssertionError, match=r"None turn"):
        expect.responds_within(None, 1.0)


def test_responds_within_fails_non_numeric_latency():
    turn = Turn(user="hi", bot="hello", metadata={"latency_ms": "fast"})
    with pytest.raises(AssertionError, match=r"expected numeric latency_ms"):
        expect.responds_within(turn, 1.0)


def test_responds_within_fails_bool_latency():
    """Guard against the bool-is-int trap: True must not pass as a latency value."""
    turn = Turn(user="hi", bot="hello", metadata={"latency_ms": True})
    with pytest.raises(AssertionError, match=r"expected numeric latency_ms"):
        expect.responds_within(turn, 1.0)


def test_responds_within_rejects_negative_budget():
    turn = Turn(user="hi", bot="hello", metadata={"latency_ms": 100})
    with pytest.raises(ValueError, match=r"non-negative"):
        expect.responds_within(turn, -0.1)


# ---------------------------------------------------------------------------
# Integration with Conversation flow
# ---------------------------------------------------------------------------


def test_matchers_work_against_real_say_flow():
    """End-to-end: adapter writes metadata, matchers read it back."""

    def bot(text, convo):
        convo.state["phase"] = "ordering"
        return "ok"

    convo = Conversation(bot=bot)
    turn = convo.say("I want a pizza")
    turn.metadata["intent"] = "order"
    turn.metadata["slots"] = {"item": "pizza"}
    turn.metadata["latency_ms"] = 42

    expect.has_intent(turn, "order")
    expect.has_slot(turn, "item", value="pizza")
    expect.has_state(convo, "phase", value="ordering")
    expect.responds_within(turn, 0.1)
