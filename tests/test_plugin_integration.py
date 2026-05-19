"""End-to-end checks that the plugin wires up through entry_points.

Each test runs a fresh inline pytest session via pytester so the assertions
verify what a real user sees after ``pip install pytest-conversational``:
fixtures resolve without an explicit import, and the ``conversational``
marker is registered cleanly under ``--strict-markers``.
"""


def test_conversation_fixture_is_discovered(pytester):
    """The ``conversation`` fixture must be available with zero imports."""
    pytester.makepyfile(
        """
        def test_uses_fixture(conversation):
            assert conversation.turns == []
            conversation.add_user("hello")
            assert conversation.turns[-1].user == "hello"
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1)


def test_conversation_factory_fixture_is_discovered(pytester):
    """The ``conversation_factory`` fixture builds adapters on demand."""
    pytester.makepyfile(
        """
        def test_uses_factory(conversation_factory):
            convo = conversation_factory(bot=lambda text, c: f"echo: {text}")
            convo.say("ping")
            assert convo.last.bot == "echo: ping"
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1)


def test_conversational_marker_does_not_warn_under_strict(pytester):
    """``@pytest.mark.conversational`` must resolve with no PytestUnknownMarkWarning."""
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational
        def test_marked(conversation):
            conversation.add_user("hi")
            assert len(conversation.turns) == 1
        """
    )
    result = pytester.runpytest("-q", "--strict-markers", "-W", "error")
    result.assert_outcomes(passed=1)


def test_conversational_marker_filters_collection(pytester):
    """``pytest -m conversational`` selects only marked tests."""
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational
        def test_picked():
            assert True

        def test_skipped():
            assert True
        """
    )
    result = pytester.runpytest("-q", "-m", "conversational")
    result.assert_outcomes(passed=1, deselected=1)
