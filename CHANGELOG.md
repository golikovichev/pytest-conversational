# Changelog

All notable changes to pytest-conversational are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Version string in `__init__.py` is now read from package metadata via `importlib.metadata.version`, removing the second source of truth.

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

[Unreleased]: https://github.com/golikovichev/pytest-conversational/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/golikovichev/pytest-conversational/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/golikovichev/pytest-conversational/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/golikovichev/pytest-conversational/releases/tag/v0.1.0
