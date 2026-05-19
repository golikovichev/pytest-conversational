"""Matchers for asserting bot replies.

Usage::

    from pytest_conversational import expect

    convo.say("hi")
    expect.contains(convo.last.bot, "hello")
    expect.regex(convo.last.bot, r"^hello\\s")
    expect.one_of(convo.last.bot, ["hi", "hey", "hello"])

Each matcher raises AssertionError with the actual bot reply embedded in
the message, so pytest output shows what the bot said versus what was
expected. Use these instead of bare ``assert`` when you want clear
diff-style failure output across many tests.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Sentinel for "any value" in has_slot / has_state. Lets callers write
#   has_slot(turn, "destination")
# meaning "the slot is set, value irrelevant", versus
#   has_slot(turn, "destination", value="Brighton")
# meaning "set AND equal".
_UNSET = object()


def contains(actual: str, substring: str, *, case_sensitive: bool = False) -> None:
    """Assert that ``substring`` appears anywhere in ``actual``.

    Case-insensitive by default. Pass ``case_sensitive=True`` for exact
    case matching.

    Raises:
        AssertionError: if ``actual`` is None or does not contain ``substring``.
    """
    if actual is None:
        raise AssertionError(f"expected substring {substring!r} in reply, got None")
    if not isinstance(substring, str):
        raise TypeError(f"substring must be str, got {type(substring).__name__}")
    haystack = actual if case_sensitive else actual.lower()
    needle = substring if case_sensitive else substring.lower()
    if needle not in haystack:
        raise AssertionError(
            f"expected substring {substring!r} in reply, got: {actual!r}"
        )


def regex(actual: str, pattern: str, *, flags: int = 0) -> re.Match[str]:
    """Assert that ``actual`` matches the regex ``pattern`` (re.search semantics).

    Returns the match object so callers can inspect captured groups.

    Raises:
        AssertionError: if ``actual`` is None or the pattern does not match.
        re.error: if ``pattern`` is not a valid regex.
    """
    if actual is None:
        raise AssertionError(f"expected regex {pattern!r} to match, got None")
    match = re.search(pattern, actual, flags=flags)
    if match is None:
        raise AssertionError(f"expected regex {pattern!r} to match, got: {actual!r}")
    return match


def one_of(
    actual: str, options: Iterable[str], *, case_sensitive: bool = False
) -> None:
    """Assert that ``actual`` is exactly equal to one of ``options``.

    Use this when the bot replies vary across deterministic alternatives,
    for example ``["yes", "yeah", "yep"]`` for affirmative answers.
    Compares full strings, not substrings. For substring search across
    several alternatives, call ``contains`` in a loop or use ``regex``.

    Case-insensitive by default. Pass ``case_sensitive=True`` for exact
    case matching.

    Raises:
        AssertionError: if ``actual`` is None or matches no option.
        ValueError: if ``options`` is empty.
    """
    opts = list(options)
    if not opts:
        raise ValueError("one_of requires at least one option")
    if actual is None:
        raise AssertionError(f"expected reply to be one of {opts!r}, got None")
    target = actual if case_sensitive else actual.lower()
    candidates = opts if case_sensitive else [o.lower() for o in opts]
    if target not in candidates:
        raise AssertionError(f"expected reply to be one of {opts!r}, got: {actual!r}")


def has_intent(turn: Any, intent_name: str) -> None:
    """Assert that ``turn.metadata["intent"]`` equals ``intent_name``.

    Adapters that do intent classification are expected to write the
    classified label into ``turn.metadata["intent"]`` after producing a
    reply. This matcher does not run a classifier itself; it only checks
    what the adapter recorded.

    Raises:
        AssertionError: if metadata has no intent, or intent differs.
    """
    if turn is None:
        raise AssertionError(f"expected intent {intent_name!r}, got None turn")
    actual = turn.metadata.get("intent") if hasattr(turn, "metadata") else None
    if actual is None:
        raise AssertionError(
            f"expected intent {intent_name!r}, turn metadata has no 'intent' key"
        )
    if actual != intent_name:
        raise AssertionError(f"expected intent {intent_name!r}, got {actual!r}")


def has_slot(turn: Any, slot_name: str, value: Any = _UNSET) -> None:
    """Assert a slot was filled on ``turn.metadata["slots"]``.

    With only a slot name, asserts the slot is present (any value).
    Pass ``value=`` to assert equality of the stored value too. Slot
    extraction is the adapter's job; this matcher only inspects what
    was recorded.

    Raises:
        AssertionError: if slots dict is missing, slot is absent, or value differs.
    """
    if turn is None:
        raise AssertionError(f"expected slot {slot_name!r}, got None turn")
    slots = turn.metadata.get("slots") if hasattr(turn, "metadata") else None
    if not isinstance(slots, dict):
        raise AssertionError(
            f"expected slot {slot_name!r}, turn metadata has no 'slots' dict"
        )
    if slot_name not in slots:
        raise AssertionError(
            f"expected slot {slot_name!r} in {sorted(slots)!r}, slot is unset"
        )
    if value is not _UNSET and slots[slot_name] != value:
        raise AssertionError(
            f"expected slot {slot_name!r}={value!r}, got {slots[slot_name]!r}"
        )


def has_state(convo: Any, state_name: str, value: Any = _UNSET) -> None:
    """Assert a key was set on ``convo.state``.

    Conversation-wide state lives on ``Conversation.state`` and persists
    across turns (slot filling, conversation phase, flags). With only a
    name, asserts the key is present. Pass ``value=`` for equality.

    Raises:
        AssertionError: if state is missing the key or value differs.
    """
    if convo is None:
        raise AssertionError(f"expected state {state_name!r}, got None conversation")
    state = convo.state if hasattr(convo, "state") else None
    if not isinstance(state, dict):
        raise AssertionError(
            f"expected state {state_name!r}, conversation has no 'state' dict"
        )
    if state_name not in state:
        raise AssertionError(
            f"expected state {state_name!r} in {sorted(state)!r}, key is unset"
        )
    if value is not _UNSET and state[state_name] != value:
        raise AssertionError(
            f"expected state {state_name!r}={value!r}, got {state[state_name]!r}"
        )


def responds_within(turn: Any, seconds: float) -> None:
    """Assert that ``turn.metadata["latency_ms"]`` is within ``seconds`` budget.

    Adapters that measure latency are expected to record reply time in
    milliseconds under ``turn.metadata["latency_ms"]``. ``seconds`` is
    expressed in seconds for readability; conversion to ms happens here.

    Raises:
        AssertionError: if latency is missing, non-numeric, or above budget.
        ValueError: if ``seconds`` is negative.
    """
    if seconds < 0:
        raise ValueError(f"seconds budget must be non-negative, got {seconds!r}")
    if turn is None:
        raise AssertionError(f"expected latency <= {seconds}s, got None turn")
    latency = turn.metadata.get("latency_ms") if hasattr(turn, "metadata") else None
    if latency is None:
        raise AssertionError(
            f"expected latency <= {seconds}s, turn metadata has no 'latency_ms' key"
        )
    if not isinstance(latency, (int, float)) or isinstance(latency, bool):
        raise AssertionError(
            f"expected numeric latency_ms, got {type(latency).__name__}: {latency!r}"
        )
    budget_ms = seconds * 1000
    if latency > budget_ms:
        raise AssertionError(
            f"expected latency <= {seconds}s ({budget_ms:.0f}ms), got {latency}ms"
        )
