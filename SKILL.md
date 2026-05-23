---
name: pytest-conversational
description: Test chat bots, voice assistants, and IVR menus with pytest using a small Conversation object and a callable bot adapter. Use when the user wants to write rule-based assertions over multi-turn dialogue without bringing in an LLM dependency, when they have a chatbot reachable as a Python callable or HTTP webhook, when they need to keep per-conversation state across turns and assert on slot filling, when they want pytest-native fixtures and a printable transcript on failure, or when they mention voice-assistant testing, IVR menu testing, conversational AI testing, LLM bot testing (used as the target under test, not as the matcher), expect matchers for bot replies, or multi-turn dialogue tests.
license: MIT
metadata:
  category: "bot-testing"
  homepage: "https://github.com/golikovichev/pytest-conversational"
  pypi: "https://pypi.org/project/pytest-conversational/"
  version: "0.3.0"
---

# pytest-conversational

A pytest plugin that gives you a `Conversation` object, a callable bot adapter, and a handful of fixtures and matchers tuned for chat-bot tests. Assertions are rule-based; there is no LLM dependency on the test side. The bot under test can be an LLM, a rule engine, an IVR menu, or any callable.

Full Public API, matcher signatures, fixture table, adapter contract, and error-handling reference live in `REFERENCE.md` next to this file.

## Quick start

1. Install:
   ```bash
   pip install pytest-conversational
   ```
   Python 3.10 and above.

2. Write a bot adapter. It is just a callable that takes user text plus the conversation and returns a reply string:
   ```python
   def my_bot(text, convo):
       if "hello" in text.lower():
           return "hi"
       return "sorry, did not get that"
   ```

3. Use the `conversation_factory` fixture in a test:
   ```python
   def test_greeting(conversation_factory):
       convo = conversation_factory(bot=my_bot)
       convo.say("hello there")
       assert convo.last.bot == "hi"
   ```

4. Run pytest as usual.

Define a callable bot, drive turns via `convo.say`, assert on `convo.last.bot` or the full transcript.

## Multi-turn state

Adapters keep per-conversation slots through `convo.state`:

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

The Conversation exposes `state` (dict), `turns` (list), `history` ([user, bot] pairs), and `transcript()` for a printable log. The plugin appends each Turn before calling the adapter, so the adapter sees the current turn in history when it runs.

## HTTP webhook adapter

If the bot is behind an HTTP endpoint, use the bundled adapter:

```bash
pip install 'pytest-conversational[http]'
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

Default contract: `POST` with JSON body `{"user": text, "history": [[u, b], ...]}`, response `{"reply": "..."}`. Pass `request_builder` and `response_parser` for other shapes. Full security guidance and override patterns are in `REFERENCE.md`.

## Matchers

`pytest_conversational.expect` gives assertion helpers with reply text embedded in failure messages:

```python
from pytest_conversational import expect

expect.contains(convo.last.bot, "hello")           # substring, case-insensitive
expect.regex(convo.last.bot, r"^hello\s+\w+")      # re.search semantics
expect.one_of(convo.last.bot, ["hi", "hey"])       # exact match against options
```

For metadata-driven matchers (`has_intent`, `has_slot`, `has_state`, `responds_within`) and full parameter signatures see `REFERENCE.md`.

## Fixtures

- `conversation`: empty Conversation, no adapter. For user-only flows.
- `conversation_factory`: builder taking a bot callable plus optional `state`.

## References

- Bundle: `REFERENCE.md` (Public API, matcher details, adapter contract, error reference)
- Project: https://github.com/golikovichev/pytest-conversational
- PyPI: https://pypi.org/project/pytest-conversational/
