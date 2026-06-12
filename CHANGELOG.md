# Changelog

All notable changes to pytest-conversational are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-12

First stable release. The public API (the `conversation` fixture, the
`expect` matchers, scenario loading, and the bot adapter protocol) is now
considered stable and follows semantic versioning from here.

### Added

- Load conversation scenarios from JSON or YAML files, so multi-turn cases can
  live as data next to the tests instead of being hand-built in Python.
- `expect.not_contains` matcher: the negative of `contains`, asserting a
  substring is absent from a reply. Useful for leak guards (bot must not echo
  an internal error, a stack trace, or a value it was never given).
  Case-insensitive by default; raises on a None reply.
- Allure transcript attachments (closes #2). `allure_attach_transcript`
  fixture serializes the Conversation as `transcript.json` (turns, state,
  metadata) and `transcript.md` (rendered turn-by-turn), then attaches both
  to the Allure report when the test fails. Optional `--conversational-always-attach`
  CLI flag also attaches on passing runs. The fixture is graceful: if
  `allure-pytest` is not installed the attach is a no-op, so the feature
  carries no hard dependency. New `allure` extra in `pyproject.toml` pulls
  `allure-pytest>=2.13` when users opt in.

## [0.4.0] - 2026-05-23

### Added

- `expect` matchers: `slot`, `state`, `intent`, and `latency` for testing
  structured conversation outputs (state machine slots, intent labels, response
  timing budgets).
- HTTP webhook adapter `allowed_hosts` parameter: pin tests to a host
  allowlist with case-insensitive comparison, trailing-dot normalisation, and
  scheme check. URLs outside the allowlist raise `ValueError` before the
  request goes out.
- Reply size guard in HTTP webhook adapter (`max_reply_bytes`, default 1 MiB):
  bound the response body size before parsing to fail fast on runaway
  adapters.
- Substring matching modes for `one_of`: contributor PR #5 by
  SHIVANSH-ux-ys.
- README badges for PyPI version, Python versions, license, and Codecov
  coverage.
- `SKILL.md` and `REFERENCE.md` for Tessl Registry submission (review score
  100%).
- Plugin smoke tests and `conversational` pytest marker registration.

### Changed

- Version string in `__init__.py` is now read from package metadata via
  `importlib.metadata.version`, removing the second source of truth.
- `say` documents partial-turn semantics: the Turn is appended to history
  before the adapter call, so adapter exceptions still leave a traceable
  transcript.
- Documentation split: `SKILL.md` contains the quick-start surface,
  `REFERENCE.md` holds the public API, matchers reference, and CI templates.

### Fixed

- HTTP webhook adapter rejects URLs with a hostname not in `allowed_hosts`
  and surfaces a clear `ValueError` instead of issuing the request.

## [0.3.0] - 2026-05-13

### Added
- `expect` matchers: `contains`, `regex`, and `one_of`, each with a `case_sensitive` keyword.
- HTTP webhook bot adapter (`pytest_conversational.adapters.http_webhook`) for testing chat backends over HTTP.

## [0.2.0] - 2026-05-09

### Added
- Bot adapter abstraction (`BotAdapter`) with state preserved across turns.
- `Conversation` and `Turn` primitives that drive multi-turn flows from pytest tests.

## [0.1.0] - 2026-05-05

### Added
- Initial release. `pyproject.toml`, CI matrix on Python 3.10 / 3.11 / 3.12, smoke tests.

[Unreleased]: https://github.com/golikovichev/pytest-conversational/compare/v0.4.0...HEAD

[0.4.0]: https://github.com/golikovichev/pytest-conversational/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/golikovichev/pytest-conversational/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/golikovichev/pytest-conversational/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/golikovichev/pytest-conversational/releases/tag/v0.1.0
