# Contributing

Thanks for your interest in pytest-conversational. This is a focused pytest plugin, so the contribution flow stays simple.

## Reporting a bug

Open an issue with:

- What you ran (pytest invocation + Python version)
- What you expected the conversation flow to do
- What happened instead (transcript on failure is in the test output)
- A minimal scenario or adapter snippet that reproduces it (strip any real bot tokens first)

## Suggesting a feature

Open an issue first so we can talk through the use case before you write code. The plugin scope is intentionally narrow: rule-based multi-turn assertions against a chat bot, voice assistant, or IVR menu, with no LLM in the loop on the test side. Feature requests that pull it elsewhere will get a polite redirect.

## Submitting a pull request

1. Fork the repo and create a branch from `main`.
2. Make your changes. Keep the diff focused on one thing.
3. Add or update tests in `tests/`. The CI runs `pytest -v` on Python 3.10, 3.11, 3.12, and 3.13.
4. Run the tests locally before pushing:
   ```bash
   pip install -e ".[dev]"
   pytest -v
   ```
5. New matchers, adapters, or expect helpers need at least one happy-path test and one failure-mode test that exercises the transcript output.
6. Open the PR with a short description of what changed and why.

## Code style

- Python 3.10+. Type hints on public functions.
- Function and variable names in English, snake_case (e.g., `assert_intent`, `match_slot`).
- One responsibility per function. If a function grows past 30-40 lines, split it.
- Ruff handles lint and formatting. Run `ruff check . && ruff format .` before opening a PR.

## Security

If you find something that could leak bot tokens, webhook secrets, or PII from a real conversation transcript, please email me directly instead of opening a public issue. Address is on my GitHub profile.
