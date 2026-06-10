"""Load conversation scenarios from JSON or YAML for parametrized tests.

A scenario file lets a single test function exercise many dialogue paths
without copying assertions for each one. The shape is intentionally small:

* A list of scenarios at the top level.
* Each scenario has a ``name`` and a list of ``turns``.
* Each turn has a ``user`` field. Optional ``expect`` / ``expect_contains``
  fields drive a default assertion in the test body, but tests are free
  to ignore them and assert their own way.

JSON is supported via the stdlib so the core package stays dependency
free. YAML loads through :mod:`yaml` and raises a clear ``ImportError``
if the optional ``scenarios`` extra is not installed.

The :func:`parametrize_scenarios` helper returns a decorator that wraps
``pytest.mark.parametrize`` with one row per scenario, ids taken from
the ``name`` field. A test function declares a single ``scenario``
parameter and walks ``scenario.turns`` inside the body.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

_YAML_EXTENSIONS = frozenset({".yaml", ".yml"})
_JSON_EXTENSIONS = frozenset({".json"})


@dataclass(frozen=True)
class ScenarioTurn:
    """One user turn plus optional expectations.

    The two ``expect*`` fields are advisory. Tests can read them to drive
    a default assertion or ignore them and write a custom assertion.
    Tests stay in control: the scenario file is data, not behaviour.
    """

    user: str
    expect: str | None = None
    expect_contains: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    """One named conversation made of an ordered list of turns."""

    name: str
    turns: tuple[ScenarioTurn, ...]
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ScenarioLoadError(ValueError):
    """Raised when a scenario file is missing, malformed, or empty."""


def _coerce_turn(raw: Any, scenario_name: str, index: int) -> ScenarioTurn:
    if not isinstance(raw, dict):
        raise ScenarioLoadError(
            f"scenario {scenario_name!r} turn {index}: expected a mapping, "
            f"got {type(raw).__name__}"
        )
    user = raw.get("user")
    if not isinstance(user, str) or not user.strip():
        raise ScenarioLoadError(
            f"scenario {scenario_name!r} turn {index}: 'user' must be a non-blank string"
        )
    expect = raw.get("expect")
    expect_contains = raw.get("expect_contains")
    if expect is not None and not isinstance(expect, str):
        raise ScenarioLoadError(
            f"scenario {scenario_name!r} turn {index}: 'expect' must be a string"
        )
    if expect_contains is not None and not isinstance(expect_contains, str):
        raise ScenarioLoadError(
            f"scenario {scenario_name!r} turn {index}: 'expect_contains' must be a string"
        )
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ScenarioLoadError(
            f"scenario {scenario_name!r} turn {index}: 'metadata' must be a mapping"
        )
    return ScenarioTurn(
        user=user,
        expect=expect,
        expect_contains=expect_contains,
        metadata=metadata,
    )


def _coerce_scenario(raw: Any, index: int) -> Scenario:
    if not isinstance(raw, dict):
        raise ScenarioLoadError(
            f"scenario at index {index}: expected a mapping, got {type(raw).__name__}"
        )
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ScenarioLoadError(
            f"scenario at index {index}: 'name' must be a non-blank string"
        )
    turns_raw = raw.get("turns")
    if not isinstance(turns_raw, list) or not turns_raw:
        raise ScenarioLoadError(f"scenario {name!r}: 'turns' must be a non-empty list")
    turns = tuple(_coerce_turn(t, name, i) for i, t in enumerate(turns_raw))
    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list) or not all(isinstance(t, str) for t in tags_raw):
        raise ScenarioLoadError(f"scenario {name!r}: 'tags' must be a list of strings")
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise ScenarioLoadError(f"scenario {name!r}: 'metadata' must be a mapping")
    return Scenario(name=name, turns=turns, tags=tuple(tags_raw), metadata=metadata)


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScenarioLoadError(
            f"invalid JSON: {exc.msg} at line {exc.lineno}"
        ) from exc


def _parse_yaml(text: str) -> Any:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "loading YAML scenarios requires the 'scenarios' extra: "
            "pip install pytest-conversational[scenarios]"
        ) from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ScenarioLoadError(f"invalid YAML: {exc}") from exc


def load_scenarios(path: str | Path) -> list[Scenario]:
    """Load scenarios from ``path``. Format is picked from the file suffix.

    Supported suffixes: ``.json``, ``.yaml``, ``.yml``. Anything else
    raises :class:`ScenarioLoadError`.

    The file must contain a top-level list. An empty list is rejected so
    parametrize never receives a zero-row iterable (pytest skips silently
    in that case, which would mask a typo in the path).
    """
    p = Path(path)
    if not p.is_file():
        raise ScenarioLoadError(f"scenario file not found: {p}")
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix in _JSON_EXTENSIONS:
        payload = _parse_json(text)
    elif suffix in _YAML_EXTENSIONS:
        payload = _parse_yaml(text)
    else:
        raise ScenarioLoadError(
            f"unsupported scenario file suffix {p.suffix!r}: use .json, .yaml, or .yml"
        )
    if not isinstance(payload, list):
        raise ScenarioLoadError(
            f"scenario file must contain a top-level list, got {type(payload).__name__}"
        )
    if not payload:
        raise ScenarioLoadError("scenario file is empty (top-level list has no items)")
    return [_coerce_scenario(s, i) for i, s in enumerate(payload)]


def parametrize_scenarios(path: str | Path, *, argname: str = "scenario"):
    """Return ``pytest.mark.parametrize`` populated from a scenario file.

    Usage:

        @parametrize_scenarios("tests/scenarios/dialogues.yaml")
        def test_dialogue(scenario, conversation_factory):
            convo = conversation_factory(bot=my_bot)
            for turn in scenario.turns:
                convo.say(turn.user)

    The ``argname`` keyword lets the user pick a different parameter
    name if ``scenario`` collides with a fixture in the project.
    """
    scenarios = load_scenarios(path)
    return pytest.mark.parametrize(
        argname,
        scenarios,
        ids=[s.name for s in scenarios],
    )


__all__ = [
    "Scenario",
    "ScenarioLoadError",
    "ScenarioTurn",
    "load_scenarios",
    "parametrize_scenarios",
]
