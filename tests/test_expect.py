"""Tests for the expect matchers module."""
from __future__ import annotations

import re

import pytest

from pytest_conversational import expect


class TestContains:
    def test_substring_present_case_insensitive_default(self) -> None:
        expect.contains("Hello there friend", "HELLO")

    def test_substring_exact_match(self) -> None:
        expect.contains("hello there", "hello")

    def test_substring_missing_raises(self) -> None:
        with pytest.raises(AssertionError, match="expected substring 'foo'"):
            expect.contains("hello there", "foo")

    def test_none_actual_raises(self) -> None:
        with pytest.raises(AssertionError, match="got None"):
            expect.contains(None, "hello")  # type: ignore[arg-type]

    def test_case_sensitive_mode(self) -> None:
        expect.contains("Hello", "Hello", case_sensitive=True)
        with pytest.raises(AssertionError):
            expect.contains("Hello", "hello", case_sensitive=True)

    def test_non_str_substring_raises_typeerror(self) -> None:
        with pytest.raises(TypeError):
            expect.contains("hello", 42)  # type: ignore[arg-type]

    def test_empty_substring_always_passes(self) -> None:
        # Empty substring is in every string, mirrors Python ``in`` semantics.
        expect.contains("anything", "")

    def test_failure_message_shows_actual(self) -> None:
        try:
            expect.contains("got something else", "expected token")
        except AssertionError as e:
            assert "got something else" in str(e)
            assert "expected token" in str(e)
        else:
            pytest.fail("expected AssertionError")


class TestRegex:
    def test_match_at_start(self) -> None:
        m = expect.regex("hello world", r"^hello")
        assert m.group(0) == "hello"

    def test_match_in_middle(self) -> None:
        m = expect.regex("say hello there", r"hello")
        assert m.group(0) == "hello"

    def test_no_match_raises(self) -> None:
        with pytest.raises(AssertionError, match="expected regex"):
            expect.regex("goodbye", r"^hello")

    def test_none_actual_raises(self) -> None:
        with pytest.raises(AssertionError, match="got None"):
            expect.regex(None, r"hello")  # type: ignore[arg-type]

    def test_flags_are_honoured(self) -> None:
        expect.regex("HELLO world", r"hello", flags=re.IGNORECASE)

    def test_invalid_pattern_raises_re_error(self) -> None:
        with pytest.raises(re.error):
            expect.regex("anything", r"(unclosed")

    def test_returns_match_object_for_capture_inspection(self) -> None:
        m = expect.regex("order 42 placed", r"order (\d+)")
        assert m.group(1) == "42"


class TestOneOf:
    def test_exact_match_first_option(self) -> None:
        expect.one_of("yes", ["yes", "yeah", "yep"])

    def test_exact_match_third_option(self) -> None:
        expect.one_of("yep", ["yes", "yeah", "yep"])

    def test_no_match_raises(self) -> None:
        with pytest.raises(AssertionError, match="expected reply to be one of"):
            expect.one_of("maybe", ["yes", "no"])

    def test_substring_match_does_not_count(self) -> None:
        # one_of requires full equality. "yeshere" contains "yes" but is not "yes".
        with pytest.raises(AssertionError):
            expect.one_of("yeshere", ["yes", "no"])

    def test_case_insensitive_default(self) -> None:
        expect.one_of("YES", ["yes", "no"])

    def test_case_sensitive_mode(self) -> None:
        expect.one_of("yes", ["yes", "no"], case_sensitive=True)
        with pytest.raises(AssertionError):
            expect.one_of("YES", ["yes", "no"], case_sensitive=True)

    def test_none_actual_raises(self) -> None:
        with pytest.raises(AssertionError, match="got None"):
            expect.one_of(None, ["yes"])  # type: ignore[arg-type]

    def test_empty_options_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="at least one option"):
            expect.one_of("yes", [])

    def test_failure_message_shows_actual_and_options(self) -> None:
        try:
            expect.one_of("nope", ["yes", "yeah"])
        except AssertionError as e:
            msg = str(e)
            assert "nope" in msg
            assert "yes" in msg
            assert "yeah" in msg
        else:
            pytest.fail("expected AssertionError")

    def test_accepts_any_iterable(self) -> None:
        expect.one_of("yes", iter(["yes", "no"]))


class TestUsageWithConversation:
    """Integration-style: matchers work on real ``convo.last.bot`` values."""

    def test_after_say(self, conversation_factory) -> None:  # type: ignore[no-untyped-def]
        def bot(text: str, convo) -> str:  # noqa: ARG001
            return "hello there"

        convo = conversation_factory(bot=bot)
        convo.say("hi")
        expect.contains(convo.last.bot, "hello")
        expect.regex(convo.last.bot, r"hello\s+\w+")
        expect.one_of(convo.last.bot, ["hello there", "hi there"])
