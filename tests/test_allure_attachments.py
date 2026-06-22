"""Tests for the Allure transcript attachment helpers and the fixture.

The helpers themselves are pure functions: they take a Conversation
and return strings, or take a Conversation and try to call allure.
We cover:

* JSON serialization shape (turns, state, metadata round-tripping)
* Markdown rendering (empty, single turn, multi-turn, state section)
* Graceful fallback when allure-pytest is not installed
* Best-effort behaviour when allure raises mid-attach
* The fixture finalizer ignoring success runs by default
* The fixture finalizer attaching on failure
* The --conversational-always-attach flag toggling success-run attach
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pytest_conversational import Conversation
from pytest_conversational.allure_attachments import (
    attach_to_allure,
    render_transcript_markdown,
    serialize_transcript_json,
)


def _build_two_turn_convo() -> Conversation:
    convo = Conversation()
    t1 = convo.add_user("hi")
    t1.bot = "hello"
    t1.metadata["intent"] = "greet"
    t2 = convo.add_user("bye")
    t2.bot = "see you"
    convo.state["session_id"] = "abc"
    return convo


def test_serialize_transcript_json_empty_conversation() -> None:
    payload = json.loads(serialize_transcript_json(Conversation()))
    assert payload == {"turns": [], "state": {}}


def test_serialize_transcript_json_round_trips_turns_state_metadata() -> None:
    convo = _build_two_turn_convo()
    payload = json.loads(serialize_transcript_json(convo))
    assert payload["state"] == {"session_id": "abc"}
    assert payload["turns"][0] == {
        "user": "hi",
        "bot": "hello",
        "metadata": {"intent": "greet"},
    }
    assert payload["turns"][1] == {"user": "bye", "bot": "see you", "metadata": {}}


def test_serialize_transcript_json_preserves_non_ascii() -> None:
    convo = Conversation()
    turn = convo.add_user("привет")
    turn.bot = "здравствуйте"
    serialized = serialize_transcript_json(convo)
    # ensure_ascii=False keeps Cyrillic readable instead of escaping
    assert "привет" in serialized
    assert "здравствуйте" in serialized


def test_render_transcript_markdown_empty_conversation() -> None:
    text = render_transcript_markdown(Conversation())
    assert text.startswith("# Conversation transcript")
    assert "empty conversation" in text


def test_render_transcript_markdown_two_turns_with_state_and_metadata() -> None:
    convo = _build_two_turn_convo()
    md = render_transcript_markdown(convo)
    assert "## Turn 1" in md
    assert "## Turn 2" in md
    # content is now wrapped in tilde fences: label on its own line, value inside
    assert "**USER:**" in md and "hi" in md
    assert "**BOT:**" in md and "hello" in md
    assert "~~~text" in md
    assert "intent" in md and "greet" in md
    assert "## State" in md
    assert "session_id" in md


def test_render_transcript_markdown_incomplete_turn_marker() -> None:
    convo = Conversation()
    convo.add_user("orphan")  # bot reply intentionally missing
    md = render_transcript_markdown(convo)
    assert "**USER:**" in md and "orphan" in md
    assert "turn incomplete" in md


def test_attach_to_allure_returns_false_when_allure_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force the import inside attach_to_allure to fail by removing any
    # cached allure module and shadowing the import lookup. We use
    # sys.modules to inject a None sentinel that raises ImportError when
    # the function tries to bind `import allure`.
    monkeypatch.setitem(sys.modules, "allure", None)
    result = attach_to_allure(_build_two_turn_convo())
    assert result is False


def test_attach_to_allure_returns_false_when_allure_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Provide a fake allure module that raises mid-attach. The helper
    # is meant to swallow the error and report False.
    fake = SimpleNamespace(
        attach=MagicMock(side_effect=RuntimeError("no allure context")),
        attachment_type=SimpleNamespace(JSON="json", MARKDOWN="markdown"),
    )
    monkeypatch.setitem(sys.modules, "allure", fake)
    result = attach_to_allure(_build_two_turn_convo())
    assert result is False


def test_attach_to_allure_returns_true_with_fake_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def _attach(content: str, name: str, attachment_type: str) -> None:
        calls.append({"content": content, "name": name, "type": attachment_type})

    fake = SimpleNamespace(
        attach=_attach,
        attachment_type=SimpleNamespace(JSON="json", MARKDOWN="markdown"),
    )
    monkeypatch.setitem(sys.modules, "allure", fake)
    convo = _build_two_turn_convo()
    result = attach_to_allure(convo, label="login")
    assert result is True
    assert len(calls) == 2
    names = {c["name"] for c in calls}
    assert names == {"login.json", "login.md"}
    types = {c["type"] for c in calls}
    assert types == {"json", "markdown"}


# --- #13 hardening: length caps and Markdown injection guard ---


def test_markdown_caps_turns_at_limit() -> None:
    from pytest_conversational.allure_attachments import MAX_TURNS_PER_ATTACHMENT

    convo = Conversation()
    over = MAX_TURNS_PER_ATTACHMENT + 100
    for i in range(over):
        t = convo.add_user(f"u{i}")
        t.bot = f"b{i}"
    md = render_transcript_markdown(convo)
    # capped: the turn just past the limit is not rendered
    assert f"## Turn {MAX_TURNS_PER_ATTACHMENT + 1}" not in md
    # truncation marker present with the original count
    assert f"[truncated, original turns: {over}]" in md


def test_json_caps_turns_at_limit() -> None:
    from pytest_conversational.allure_attachments import MAX_TURNS_PER_ATTACHMENT

    convo = Conversation()
    over = MAX_TURNS_PER_ATTACHMENT + 50
    for i in range(over):
        convo.add_user(f"u{i}")
    payload = json.loads(serialize_transcript_json(convo))
    assert len(payload["turns"]) == MAX_TURNS_PER_ATTACHMENT
    assert payload["truncated_turns"] == over


def test_zero_max_turns_means_unlimited() -> None:
    convo = Conversation()
    for i in range(5):
        convo.add_user(f"u{i}")
    md = render_transcript_markdown(convo, max_turns=0)
    assert "## Turn 5" in md
    assert "truncated, original turns" not in md
    payload = json.loads(serialize_transcript_json(convo, max_turns=0))
    assert len(payload["turns"]) == 5
    assert "truncated_turns" not in payload


def test_markdown_caps_field_chars() -> None:
    from pytest_conversational.allure_attachments import MAX_CHARS_PER_FIELD

    convo = Conversation()
    big = "x" * (MAX_CHARS_PER_FIELD + 5000)
    t = convo.add_user(big)
    t.bot = "ok"
    md = render_transcript_markdown(convo)
    assert f"[truncated, original chars: {len(big)}]" in md
    # the full oversized field is not present verbatim
    assert big not in md
    # exactly MAX_CHARS_PER_FIELD chars kept, not fewer
    assert "x" * MAX_CHARS_PER_FIELD in md
    assert "x" * (MAX_CHARS_PER_FIELD + 1) not in md


def test_json_caps_metadata_field_chars() -> None:
    from pytest_conversational.allure_attachments import MAX_CHARS_PER_FIELD

    convo = Conversation()
    big = "y" * (MAX_CHARS_PER_FIELD + 100)
    t = convo.add_user("u")
    t.metadata["note"] = big
    payload = json.loads(serialize_transcript_json(convo))
    note = payload["turns"][0]["metadata"]["note"]
    assert big not in note
    assert "[truncated, original chars:" in note


def test_json_keeps_non_string_metadata_raw() -> None:
    convo = Conversation()
    t = convo.add_user("u")
    t.metadata["count"] = 3
    t.metadata["ok"] = True
    payload = json.loads(serialize_transcript_json(convo))
    meta = payload["turns"][0]["metadata"]
    assert meta == {"count": 3, "ok": True}


def test_markdown_injection_user_content_fenced() -> None:
    convo = Conversation()
    t1 = convo.add_user("```\n# pwned heading\n<script>alert(1)</script>")
    t1.bot = "safe"
    convo.add_user("second")
    md = render_transcript_markdown(convo)
    # the payload sits right after a tilde fence open, so the renderer shows
    # it as text instead of executing the heading / backticks / HTML
    assert "~~~text\n```\n# pwned heading\n<script>alert(1)</script>" in md
    # subsequent turn structure survives the injection attempt
    assert "## Turn 2" in md


def test_attach_to_allure_passes_caps_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def _attach(content: str, name: str, attachment_type: str) -> None:
        captured[name] = content

    fake = SimpleNamespace(
        attach=_attach,
        attachment_type=SimpleNamespace(JSON="json", MARKDOWN="markdown"),
    )
    monkeypatch.setitem(sys.modules, "allure", fake)
    convo = Conversation()
    for i in range(5):
        convo.add_user(f"u{i}")
    attach_to_allure(convo, max_turns=2)
    assert "[truncated, original turns: 5]" in captured["conversation.md"]
    assert "truncated_turns" in captured["conversation.json"]


def test_markdown_fence_escapes_nested_tilde_fence() -> None:
    convo = Conversation()
    t = convo.add_user("~~~text\nbreakout\n~~~")
    t.bot = "ok"
    md = render_transcript_markdown(convo)
    # outer fence must be longer than any tilde run in the content
    assert "~~~~" in md


# --- Fixture-level integration tests using pytester ---


def test_fixture_no_attach_on_passing_test(pytester: pytest.Pytester) -> None:
    """Without the --conversational-always-attach flag, a passing test
    should not invoke attach_to_allure. We assert by patching the helper
    and counting calls."""
    pytester.makepyfile(
        test_pass="""
        from pytest_conversational import Conversation


        def test_passes(conversation, allure_attach_transcript):
            conversation.add_user("ok")
            assert True
        """
    )
    pytester.makeconftest(
        """
        import pytest
        from pytest_conversational import allure_attachments

        attach_calls = []

        @pytest.fixture(autouse=True)
        def _track_attach(monkeypatch):
            def fake_attach(conv, label="conversation", **kwargs):
                attach_calls.append((conv, label))
                return True
            monkeypatch.setattr(allure_attachments, "attach_to_allure", fake_attach)
            # Also patch the plugin's imported alias
            import pytest_conversational.plugin as plugin
            monkeypatch.setattr(plugin, "attach_to_allure", fake_attach)
            yield

        def pytest_sessionfinish(session, exitstatus):
            # write count к a file pytester can read back
            with open(str(session.config.rootpath / "attach_count.txt"), "w") as f:
                f.write(str(len(attach_calls)))
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1)
    count_file = pytester.path / "attach_count.txt"
    assert count_file.read_text().strip() == "0"


def test_fixture_attaches_on_failure(pytester: pytest.Pytester) -> None:
    """On test failure the fixture finalizer должен walk fixtures and call
    attach_to_allure for each Conversation it finds."""
    pytester.makepyfile(
        test_fail="""
        from pytest_conversational import Conversation


        def test_fails(conversation, allure_attach_transcript):
            conversation.add_user("boom")
            assert False, "intentional"
        """
    )
    pytester.makeconftest(
        """
        import pytest
        from pytest_conversational import allure_attachments

        attach_calls = []

        @pytest.fixture(autouse=True)
        def _track_attach(monkeypatch):
            def fake_attach(conv, label="conversation", **kwargs):
                attach_calls.append((conv, label))
                return True
            monkeypatch.setattr(allure_attachments, "attach_to_allure", fake_attach)
            import pytest_conversational.plugin as plugin
            monkeypatch.setattr(plugin, "attach_to_allure", fake_attach)
            yield

        def pytest_sessionfinish(session, exitstatus):
            with open(str(session.config.rootpath / "attach_count.txt"), "w") as f:
                f.write(str(len(attach_calls)))
            with open(str(session.config.rootpath / "attach_labels.txt"), "w") as f:
                f.write(",".join(label for _, label in attach_calls))
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(failed=1)
    count = (pytester.path / "attach_count.txt").read_text().strip()
    labels = (pytester.path / "attach_labels.txt").read_text().strip()
    assert count == "1"
    assert labels == "conversation"


def test_fixture_attaches_on_always_attach_flag(pytester: pytest.Pytester) -> None:
    """--conversational-always-attach should trigger attach on a passing test too."""
    pytester.makepyfile(
        test_always="""
        from pytest_conversational import Conversation


        def test_passes(conversation, allure_attach_transcript):
            conversation.add_user("ok")
        """
    )
    pytester.makeconftest(
        """
        import pytest
        from pytest_conversational import allure_attachments

        attach_calls = []

        @pytest.fixture(autouse=True)
        def _track_attach(monkeypatch):
            def fake_attach(conv, label="conversation", **kwargs):
                attach_calls.append((conv, label))
                return True
            monkeypatch.setattr(allure_attachments, "attach_to_allure", fake_attach)
            import pytest_conversational.plugin as plugin
            monkeypatch.setattr(plugin, "attach_to_allure", fake_attach)
            yield

        def pytest_sessionfinish(session, exitstatus):
            with open(str(session.config.rootpath / "attach_count.txt"), "w") as f:
                f.write(str(len(attach_calls)))
        """
    )
    result = pytester.runpytest("-q", "--conversational-always-attach")
    result.assert_outcomes(passed=1)
    count = (pytester.path / "attach_count.txt").read_text().strip()
    assert count == "1"


def test_fixture_explicit_register_call(pytester: pytest.Pytester) -> None:
    """Tests can call the fixture's returned function to register an
    arbitrary Conversation with a custom label. These should always be
    attached at teardown, even on a passing run, regardless of the flag."""
    pytester.makepyfile(
        test_explicit="""
        from pytest_conversational import Conversation


        def test_passes(allure_attach_transcript):
            convo_a = Conversation()
            convo_a.add_user("first")
            convo_b = Conversation()
            convo_b.add_user("second")
            allure_attach_transcript(convo_a, label="alpha")
            allure_attach_transcript(convo_b, label="beta")
        """
    )
    pytester.makeconftest(
        """
        import pytest
        from pytest_conversational import allure_attachments

        attach_calls = []

        @pytest.fixture(autouse=True)
        def _track_attach(monkeypatch):
            def fake_attach(conv, label="conversation", **kwargs):
                attach_calls.append((conv, label))
                return True
            monkeypatch.setattr(allure_attachments, "attach_to_allure", fake_attach)
            import pytest_conversational.plugin as plugin
            monkeypatch.setattr(plugin, "attach_to_allure", fake_attach)
            yield

        def pytest_sessionfinish(session, exitstatus):
            with open(str(session.config.rootpath / "attach_labels.txt"), "w") as f:
                f.write(",".join(label for _, label in attach_calls))
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1)
    labels = (pytester.path / "attach_labels.txt").read_text().strip()
    assert labels == "alpha,beta"


def test_pytest_ini_caps_passed_to_attach(pytester: pytest.Pytester) -> None:
    """conversational_max_turns / conversational_max_chars in pytest.ini are
    read by the plugin and threaded into attach_to_allure as ints."""
    pytester.makeini(
        """
        [pytest]
        conversational_max_turns = 2
        conversational_max_chars = 50
        """
    )
    pytester.makepyfile(
        test_ini="""
        def test_fails(conversation, allure_attach_transcript):
            conversation.add_user("boom")
            assert False, "intentional"
        """
    )
    pytester.makeconftest(
        """
        import pytest
        from pytest_conversational import allure_attachments

        captured = {}

        @pytest.fixture(autouse=True)
        def _track_attach(monkeypatch):
            def fake_attach(conv, label="conversation", max_turns=None, max_chars=None):
                captured["max_turns"] = max_turns
                captured["max_chars"] = max_chars
                return True
            monkeypatch.setattr(allure_attachments, "attach_to_allure", fake_attach)
            import pytest_conversational.plugin as plugin
            monkeypatch.setattr(plugin, "attach_to_allure", fake_attach)
            yield

        def pytest_sessionfinish(session, exitstatus):
            with open(str(session.config.rootpath / "caps.txt"), "w") as f:
                f.write(f"{captured.get('max_turns')},{captured.get('max_chars')}")
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(failed=1)
    caps = (pytester.path / "caps.txt").read_text().strip()
    assert caps == "2,50"
