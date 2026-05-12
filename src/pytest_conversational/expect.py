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
from typing import Iterable


def contains(actual: str, substring: str, *, case_sensitive: bool = False) -> None:
    """Assert that ``substring`` appears anywhere in ``actual``.

    Case-insensitive by default. Pass ``case_sensitive=True`` for exact
    case matching.

    Raises:
        AssertionError: if ``actual`` is None or does not contain ``substring``.
    """
    if actual is None:
        raise AssertionError(
            f"expected substring {substring!r} in reply, got None"
        )
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
        raise AssertionError(
            f"expected regex {pattern!r} to match, got None"
        )
    match = re.search(pattern, actual, flags=flags)
    if match is None:
        raise AssertionError(
            f"expected regex {pattern!r} to match, got: {actual!r}"
        )
    return match


def one_of(actual: str, options: Iterable[str], *, case_sensitive: bool = False) -> None:
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
        raise AssertionError(
            f"expected reply to be one of {opts!r}, got None"
        )
    target = actual if case_sensitive else actual.lower()
    candidates = opts if case_sensitive else [o.lower() for o in opts]
    if target not in candidates:
        raise AssertionError(
            f"expected reply to be one of {opts!r}, got: {actual!r}"
        )
