# pytest-conversational

[![PyPI](https://img.shields.io/pypi/v/pytest-conversational.svg)](https://pypi.org/project/pytest-conversational/)
[![Python versions](https://img.shields.io/pypi/pyversions/pytest-conversational.svg)](https://pypi.org/project/pytest-conversational/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A pytest plugin for testing chat bots, voice assistants, IVR menus. Rule-based assertions, no LLM dependency.

Status: alpha. v1.0.0 target June 2026.

## Why

Most chat-bot test setups fall into one of two camps. Either a pile of `requests.post` calls with hand-rolled assertions, or a heavy framework that pins you to one platform. This plugin sits in the middle: a small `Conversation` object, a callable bot adapter, and pytest fixtures that wire them together.

You bring the bot. The plugin keeps turn order and per-conversation state, then prints a transcript when an assertion fails.

## Install

```bash
pip install pytest-conversational
```

Python 3.10 and above.

## Quick start

```python
def my_bot(text, convo):
    if "hello" in text.lower():
        return "hi"
    return "sorry, did not get that"


def test_greeting(conversation_factory):
    convo = conversation_factory(bot=my_bot)
    convo.say("hello there")
    assert convo.last.bot == "hi"
```

## Multi-turn state

Adapters can read `convo.state` and `convo.turns` to keep slots between turns:

```python
def slot_filling_bot(text, convo):
    slots = convo.state.setdefault("slots", {})
    if "name" not in slots:
        slots["name"] = text
        return "got it, what city?"
    if "city" not in slots:
        slots["city"] = text
        return f"hello {slots['name']} from {slots['city']}"
    return "done"


def test_two_slot_flow(conversation_factory):
    convo = conversation_factory(bot=slot_filling_bot)
    convo.say("Mikhail")
    convo.say("Hove")
    assert convo.state["slots"] == {"name": "Mikhail", "city": "Hove"}
    assert convo.last.bot == "hello Mikhail from Hove"
```

## HTTP webhook adapter

If your bot lives behind an HTTP endpoint, use the bundled adapter instead of writing one by hand:

```bash
pip install pytest-conversational[http]
```

```python
from pytest_conversational import Conversation
from pytest_conversational.adapters import http_webhook


def test_remote_bot():
    bot = http_webhook("https://my-bot.example.com/webhook", timeout=3.0)
    convo = Conversation(bot=bot)
    convo.say("hello")
    assert "hi" in convo.last.bot.lower()
```

The default contract: POST `{"user": text, "history": [[u, b], ...]}`, expect `200 OK` with JSON `{"reply": "..."}`. If your endpoint speaks a different shape, pass `request_builder` and `response_parser` callbacks.

### Security note

The webhook URL is passed through to `httpx` as-is. If your test feeds a URL it pulled from user input, fixture data, or another untrusted source, the adapter will happily hit it. That includes internal addresses like `127.0.0.1`, `169.254.169.254` (cloud metadata service), or `10.x.x.x` inside a VPC. Pin the URL to a hard-coded value in the test, or gate it through your own allowlist before passing it in.

## Matchers

`expect` is a small module of assertion helpers tuned for bot replies. Each matcher raises `AssertionError` with the actual reply embedded in the message, so pytest output shows what the bot said versus what the test wanted.

```python
from pytest_conversational import expect

def test_replies(conversation_factory):
    convo = conversation_factory(bot=my_bot)
    convo.say("hi")

    expect.contains(convo.last.bot, "hello")
    expect.regex(convo.last.bot, r"^hello\s+\w+")
    expect.one_of(convo.last.bot, ["hello there", "hi there", "hey"])
```

- `contains(actual, substring, *, case_sensitive=False)`: substring search. Case-insensitive by default.
- `regex(actual, pattern, *, flags=0)`: `re.search` semantics. Returns the match object so callers can inspect captured groups.
- `one_of(actual, options, *, case_sensitive=False, mode="exact")`: matches `actual` against a list of alternative `options`. Supports `mode="exact"` (full-string match, default) and `mode="substring"` (checks if any option is a substring of `actual`).

Use these when bare `assert "hello" in convo.last.bot` would give noisy failure messages across many tests. For one-off checks, plain `assert` is still fine.

## Fixtures

| Fixture | Purpose |
| --- | --- |
| `conversation` | Empty Conversation, no adapter. Good for user-only flows. |
| `conversation_factory` | Builder. Pass a bot callable, get a fresh Conversation. |

## Public API

- `Conversation(bot=None, turns=[], state={})`
- `Conversation.say(text)`: drive a turn through the adapter, return the Turn.
- `Conversation.add_user(text)`: append a user-only turn.
- `Conversation.last`, `.turns`, `.history`, `.transcript()`.
- `Turn(user, bot, metadata)`.
- `BotAdapter = Callable[[str, Conversation], str]`.
- `expect.contains`, `expect.regex`, `expect.one_of`.

## Roadmap

- v0.4: scenario DSL loaded from YAML or plain text fixtures.
- v0.5: async adapter support for coroutine-based bots.
- v1.0: 12.06.2026 release.

## Licence

MIT. See `LICENSE`.
