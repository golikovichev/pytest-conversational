"""Tests for the scenarios loader and parametrize helper."""

from __future__ import annotations

import json
import textwrap

import pytest

from pytest_conversational.scenarios import (
    Scenario,
    ScenarioLoadError,
    ScenarioTurn,
    load_scenarios,
)

yaml = pytest.importorskip("yaml")


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


# ----------------------------- JSON loading -----------------------------


def test_load_json_happy_path(tmp_path):
    payload = [
        {
            "name": "greeting",
            "turns": [
                {"user": "Hi"},
                {"user": "Bye", "expect": "Goodbye"},
            ],
        },
        {
            "name": "order",
            "turns": [{"user": "I want a pizza", "expect_contains": "pizza"}],
            "tags": ["food", "happy-path"],
        },
    ]
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    scenarios = load_scenarios(path)
    assert len(scenarios) == 2
    assert scenarios[0].name == "greeting"
    assert scenarios[0].turns[1].expect == "Goodbye"
    assert scenarios[1].tags == ("food", "happy-path")
    assert scenarios[1].turns[0].expect_contains == "pizza"
    assert isinstance(scenarios[0], Scenario)
    assert isinstance(scenarios[0].turns[0], ScenarioTurn)


def test_load_json_metadata_propagates(tmp_path):
    payload = [
        {
            "name": "with-meta",
            "metadata": {"locale": "en-GB"},
            "turns": [{"user": "Hi", "metadata": {"intent": "greet"}}],
        }
    ]
    path = tmp_path / "s.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    [scenario] = load_scenarios(path)
    assert scenario.metadata == {"locale": "en-GB"}
    assert scenario.turns[0].metadata == {"intent": "greet"}


def test_load_json_invalid_syntax(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="invalid JSON"):
        load_scenarios(path)


def test_load_json_top_level_must_be_list(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "x"}), encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="top-level list"):
        load_scenarios(path)


def test_load_empty_list_rejected(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="empty"):
        load_scenarios(path)


# ----------------------------- YAML loading -----------------------------


def test_load_yaml_happy_path(tmp_path):
    content = """
    - name: greeting
      turns:
        - user: Hi
        - user: Bye
          expect: Goodbye
    - name: order
      tags: [food]
      turns:
        - user: I want a pizza
          expect_contains: pizza
    """
    path = _write(tmp_path, "scenarios.yaml", content)
    scenarios = load_scenarios(path)
    assert [s.name for s in scenarios] == ["greeting", "order"]
    assert scenarios[1].tags == ("food",)


def test_load_yml_extension_also_supported(tmp_path):
    content = """
    - name: only
      turns:
        - user: hello
    """
    path = _write(tmp_path, "s.yml", content)
    scenarios = load_scenarios(path)
    assert scenarios[0].name == "only"


# ----------------------------- Error surfaces -----------------------------


def test_missing_file(tmp_path):
    with pytest.raises(ScenarioLoadError, match="not found"):
        load_scenarios(tmp_path / "nope.json")


def test_unsupported_suffix(tmp_path):
    path = tmp_path / "weird.txt"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="unsupported scenario file suffix"):
        load_scenarios(path)


def test_scenario_missing_name(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([{"turns": [{"user": "Hi"}]}]), encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="'name'"):
        load_scenarios(path)


def test_scenario_blank_name(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"name": "   ", "turns": [{"user": "Hi"}]}]), encoding="utf-8"
    )
    with pytest.raises(ScenarioLoadError, match="'name'"):
        load_scenarios(path)


def test_scenario_empty_turns(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([{"name": "x", "turns": []}]), encoding="utf-8")
    with pytest.raises(ScenarioLoadError, match="non-empty"):
        load_scenarios(path)


def test_turn_user_must_be_string(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"name": "x", "turns": [{"user": 42}]}]), encoding="utf-8"
    )
    with pytest.raises(ScenarioLoadError, match="'user' must be a non-blank string"):
        load_scenarios(path)


def test_turn_expect_must_be_string(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"name": "x", "turns": [{"user": "Hi", "expect": 42}]}]),
        encoding="utf-8",
    )
    with pytest.raises(ScenarioLoadError, match="'expect' must be a string"):
        load_scenarios(path)


def test_turn_expect_contains_must_be_string(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"name": "x", "turns": [{"user": "Hi", "expect_contains": 42}]}]),
        encoding="utf-8",
    )
    with pytest.raises(ScenarioLoadError, match="'expect_contains' must be a string"):
        load_scenarios(path)


def test_scenario_tags_must_be_list_of_strings(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"name": "x", "tags": [1, 2], "turns": [{"user": "Hi"}]}]),
        encoding="utf-8",
    )
    with pytest.raises(ScenarioLoadError, match="'tags' must be a list of strings"):
        load_scenarios(path)


def test_top_level_not_list_in_yaml(tmp_path):
    path = _write(tmp_path, "bad.yaml", "name: x\n")
    with pytest.raises(ScenarioLoadError, match="top-level list"):
        load_scenarios(path)


def test_duplicate_scenario_names_rejected(tmp_path):
    # names become parametrize ids; duplicates make pytest mangle ids and break
    # `-k name` targeting, so reject them at load time with a clear error.
    path = tmp_path / "dup.json"
    path.write_text(
        json.dumps(
            [
                {"name": "greet", "turns": [{"user": "hi"}]},
                {"name": "order", "turns": [{"user": "pizza"}]},
                {"name": "greet", "turns": [{"user": "hello again"}]},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ScenarioLoadError, match="duplicate scenario name 'greet'"):
        load_scenarios(path)


# ----------------------------- Parametrize helper -----------------------------


def test_parametrize_decorator_runs(tmp_path, pytester):
    scenarios_path = tmp_path / "s.json"
    scenarios_path.write_text(
        json.dumps(
            [
                {"name": "a", "turns": [{"user": "hi"}]},
                {"name": "b", "turns": [{"user": "bye"}]},
            ]
        ),
        encoding="utf-8",
    )
    pytester.makepyfile(
        f"""
        from pytest_conversational.scenarios import parametrize_scenarios

        @parametrize_scenarios(r"{scenarios_path}")
        def test_dialogue(scenario):
            assert scenario.turns[0].user in {{"hi", "bye"}}
        """
    )
    result = pytester.runpytest("-v")
    result.assert_outcomes(passed=2)
    assert "test_dialogue[a]" in result.stdout.str()
    assert "test_dialogue[b]" in result.stdout.str()


def test_parametrize_custom_argname(tmp_path, pytester):
    scenarios_path = tmp_path / "s.json"
    scenarios_path.write_text(
        json.dumps([{"name": "x", "turns": [{"user": "hi"}]}]),
        encoding="utf-8",
    )
    pytester.makepyfile(
        f"""
        from pytest_conversational.scenarios import parametrize_scenarios

        @parametrize_scenarios(r"{scenarios_path}", argname="case")
        def test_dialogue(case):
            assert case.name == "x"
        """
    )
    result = pytester.runpytest("-v")
    result.assert_outcomes(passed=1)


# --------------------------- Immutability + frozenness ---------------------------


def test_scenario_is_frozen():
    s = Scenario(name="x", turns=())
    with pytest.raises((AttributeError, Exception)):
        s.name = "y"  # type: ignore[misc]


def test_scenario_turn_is_frozen():
    t = ScenarioTurn(user="hi")
    with pytest.raises((AttributeError, Exception)):
        t.user = "bye"  # type: ignore[misc]
