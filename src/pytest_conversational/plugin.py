"""pytest plugin entry. Provides the ``conversation`` fixture and a builder."""

from typing import Callable, Optional

import pytest

from pytest_conversational.allure_attachments import (
    MAX_CHARS_PER_FIELD,
    MAX_TURNS_PER_ATTACHMENT,
    attach_to_allure,
)
from pytest_conversational.conversation import BotAdapter, Conversation


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``conversational`` marker so ``--strict-markers`` is happy.

    Tests that exercise multi-turn dialogue can opt in with::

        @pytest.mark.conversational
        def test_greeting(conversation_factory):
            ...

    Collection filtering then works as expected: ``pytest -m conversational``.
    """
    config.addinivalue_line(
        "markers",
        "conversational: tag a test as a multi-turn conversational bot test",
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register CLI options for the conversational plugin.

    --conversational-always-attach: attach the transcript to Allure on
    successful runs too, not only on failure. Default off so passing
    builds stay quiet.
    """
    parser.addoption(
        "--conversational-always-attach",
        action="store_true",
        default=False,
        help=(
            "Attach Conversation transcripts to Allure on success as well as "
            "failure. By default the plugin only attaches when a test fails."
        ),
    )
    parser.addini(
        "conversational_max_turns",
        help="Max conversation turns per Allure attachment before truncation.",
        default=str(MAX_TURNS_PER_ATTACHMENT),
    )
    parser.addini(
        "conversational_max_chars",
        help="Max characters per transcript field before truncation.",
        default=str(MAX_CHARS_PER_FIELD),
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Stash each phase report on the item so fixture finalizers can read outcome.

    pytest does not expose the outcome to fixture teardown directly. The
    standard workaround is this hookwrapper: yield, then grab the result
    and attach it as ``rep_setup`` / ``rep_call`` / ``rep_teardown`` for
    later inspection. The ``allure_attach_transcript`` fixture reads
    ``item.rep_call`` to decide whether to attach.
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture
def conversation() -> Conversation:
    """Fresh empty Conversation, no adapter attached.

    Suitable for user-only flows or tests that pre-load turns by hand.
    For tests that need a bot, request ``conversation_factory`` instead.
    """
    return Conversation()


@pytest.fixture
def conversation_factory():
    """Factory that builds a Conversation with a chosen bot adapter.

    Example::

        def test_greeting(conversation_factory):
            convo = conversation_factory(bot=lambda text, c: "hi")
            convo.say("hello")
            assert convo.last.bot == "hi"
    """

    def _build(bot: Optional[BotAdapter] = None) -> Conversation:
        return Conversation(bot=bot)

    return _build


@pytest.fixture
def allure_attach_transcript(request: pytest.FixtureRequest) -> Callable[..., None]:
    """Opt-in fixture that attaches Conversation transcripts to Allure.

    Usage::

        def test_dialogue(conversation, allure_attach_transcript):
            conversation.add_user("hi")
            ...

    Default behaviour: on test failure the fixture finalizer walks the
    test's other fixtures, picks every Conversation it finds, and calls
    :func:`attach_to_allure` for each. On success the finalizer is a
    no-op unless ``--conversational-always-attach`` was passed.

    Callers that need explicit control can call the returned function
    directly with their own Conversation::

        def test_dialogue(allure_attach_transcript):
            convo = build_my_convo()
            ...
            allure_attach_transcript(convo, label="login_flow")

    Conversations registered this way are tracked alongside the
    auto-discovered ones and are always attached, regardless of
    outcome, at teardown.

    If allure-pytest is not installed the fixture still works: the
    underlying :func:`attach_to_allure` is best-effort and returns
    False silently.
    """
    registered: list[tuple[Conversation, str]] = []

    def _register(conversation: Conversation, label: str = "conversation") -> None:
        registered.append((conversation, label))

    yield _register

    # Teardown: decide whether to attach based on the outcome the
    # makereport hook stashed on the item, plus the CLI flag.
    rep_call = getattr(request.node, "rep_call", None)
    rep_setup = getattr(request.node, "rep_setup", None)
    failed = (rep_call is not None and rep_call.failed) or (
        rep_setup is not None and rep_setup.failed
    )
    always = request.config.getoption("--conversational-always-attach", default=False)
    auto_attach = failed or always

    if not auto_attach and not registered:
        return

    if auto_attach:
        # Auto-discover any Conversation in fixtures already resolved
        # for this test. pytest stores resolved fixture values on the
        # item as ``funcargs`` once the test function has been called,
        # so this lookup is safe during teardown. Conversations
        # explicitly registered through _register are appended below so
        # ordering preserves the user's labels.
        seen_ids: set[int] = {id(c) for c, _ in registered}
        funcargs = getattr(request.node, "funcargs", {}) or {}
        for name, value in funcargs.items():
            if isinstance(value, Conversation) and id(value) not in seen_ids:
                registered.append((value, name))
                seen_ids.add(id(value))

    def _ini_int(name: str, fallback: int) -> int:
        raw = request.config.getini(name)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return fallback

    max_turns = _ini_int("conversational_max_turns", MAX_TURNS_PER_ATTACHMENT)
    max_chars = _ini_int("conversational_max_chars", MAX_CHARS_PER_FIELD)

    for conversation, label in registered:
        attach_to_allure(
            conversation, label=label, max_turns=max_turns, max_chars=max_chars
        )
