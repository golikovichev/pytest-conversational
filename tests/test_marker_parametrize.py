"""Marker-driven scenario parametrization (#1).

``@pytest.mark.conversational(data="cases.json")`` loads the scenario file and
generates one test per case (id = scenario name), and a case may name fixtures
to override (e.g. a different bot adapter per locale). These run through
``pytester`` so they exercise the real entry-point wiring a user gets.
"""


def test_marker_parametrizes_one_test_per_case(pytester):
    pytester.makefile(
        ".json",
        cases='[{"name": "alpha", "turns": [{"user": "hi"}]}, '
        '{"name": "beta", "turns": [{"user": "yo"}]}]',
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational(data="cases.json")
        def test_flow(scenario):
            assert scenario.name in ("alpha", "beta")
            assert scenario.turns[0].user in ("hi", "yo")
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2)


def test_each_case_id_is_the_scenario_name(pytester):
    pytester.makefile(
        ".json",
        cases='[{"name": "english_path", "turns": [{"user": "hi"}]}, '
        '{"name": "russian_path", "turns": [{"user": "hi"}]}]',
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational(data="cases.json")
        def test_flow(scenario):
            pass
        """
    )
    result = pytester.runpytest("--collect-only", "-q")
    result.stdout.fnmatch_lines(
        ["*test_flow*english_path*", "*test_flow*russian_path*"]
    )


def test_per_case_bot_fixture_override(pytester):
    pytester.makefile(
        ".json",
        cases='[{"name": "en", "fixtures": {"bot": "en_bot"}, '
        '"turns": [{"user": "hi", "expect_contains": "hello"}]}, '
        '{"name": "ru", "fixtures": {"bot": "ru_bot"}, '
        '"turns": [{"user": "privet", "expect_contains": "zdrav"}]}]',
    )
    pytester.makeconftest(
        """
        import pytest

        @pytest.fixture
        def en_bot():
            return lambda text, convo: "hello there"

        @pytest.fixture
        def ru_bot():
            return lambda text, convo: "zdravstvuyte"
        """
    )
    pytester.makepyfile(
        """
        import pytest
        from pytest_conversational import expect

        @pytest.mark.conversational(data="cases.json")
        def test_flow(scenario, scenario_fixtures, conversation_factory):
            convo = conversation_factory(bot=scenario_fixtures["bot"])
            for turn in scenario.turns:
                convo.say(turn.user)
                if turn.expect_contains:
                    expect.contains(convo.last.bot, turn.expect_contains)
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2)


def test_scenario_without_overrides_has_empty_fixtures(pytester):
    pytester.makefile(
        ".json",
        cases='[{"name": "plain", "turns": [{"user": "hi"}]}]',
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational(data="cases.json")
        def test_flow(scenario, scenario_fixtures):
            assert scenario.fixtures == {}
            assert scenario_fixtures == {}
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1)


def test_malformed_fixtures_block_gives_clear_error(pytester):
    pytester.makefile(
        ".json",
        bad='[{"name": "x", "fixtures": "not-a-mapping", "turns": [{"user": "hi"}]}]',
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational(data="bad.json")
        def test_flow(scenario):
            pass
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*fixtures*mapping*"])


def test_missing_data_file_gives_clear_error(pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational(data="nope.json")
        def test_flow(scenario):
            pass
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*not found*"])


def test_marker_without_data_is_still_a_plain_tag(pytester):
    """A bare ``@pytest.mark.conversational`` (no data=) must not try to load."""
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational
        def test_tagged(conversation):
            conversation.add_user("hi")
            assert len(conversation.turns) == 1
        """
    )
    result = pytester.runpytest("-q", "--strict-markers")
    result.assert_outcomes(passed=1)


def test_scenario_fixture_outside_marker_gives_clear_error(pytester):
    """Requesting ``scenario`` with no data marker errors with guidance, not a
    raw AttributeError into plugin internals."""
    pytester.makepyfile(
        """
        def test_no_marker(scenario):
            pass
        """
    )
    result = pytester.runpytest("-q")
    result.stdout.fnmatch_lines(["*conversational(data*"])


def test_data_marker_without_scenario_arg_warns(pytester):
    """``data=`` set but the test forgot the ``scenario`` arg would silently
    produce one un-parametrized test; warn so the typo is not masked."""
    pytester.makefile(
        ".json",
        cases='[{"name": "a", "turns": [{"user": "hi"}]}]',
    )
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.conversational(data="cases.json")
        def test_forgot_arg():
            pass
        """
    )
    result = pytester.runpytest("-q")
    result.stdout.fnmatch_lines(["*takes no*scenario*"])
