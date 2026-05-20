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

## Quick start

1. Install the plugin from PyPI:
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

4. Run pytest as usual:
   ```bash
   pytest -v
   ```

That is the whole loop: define a callable bot, drive turns via `convo.say`, assert on `convo.last.bot` or the full transcript.

### Error handling

- **Adapter raised an exception:** the exception propagates unchanged. Tests pattern-match on the concrete type (`pytest.raises(MyAdapterError)`).
- **Webhook body too large:** the bundled `http_webhook` adapter accepts `max_reply_bytes` (default 1 MiB). A larger response raises before JSON parse.
- **Wrong reply shape:** the default webhook contract expects `{"reply": "..."}` on the response. Override with `response_parser` if your endpoint speaks a different shape.

## Multi-turn state

Adapters can keep per-conversation slots through `convo.state`:

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

The Conversation object exposes `state` (dict), `turns` (list of Turn), `history` (list of `[user, bot]` pairs), and `transcript()` for a printable log. The plugin appends the Turn before calling the adapter, so the adapter always sees the current turn in history when it runs.

## HTTP webhook adapter

If the bot is behind an HTTP endpoint, use the bundled adapter instead of writing one by hand:

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

Default contract:

- Request: `POST` with JSON body `{"user": text, "history": [[u, b], ...]}`
- Response: `200 OK` with JSON `{"reply": "..."}`

Pass `request_builder` and `response_parser` callables to talk to endpoints that use a different shape.

### Security note

The webhook URL is passed through to `httpx` as-is. If a test reads the URL from fixture data, an env file, or any other untrusted source, the adapter will happily hit it, including internal addresses such as `127.0.0.1`, `169.254.169.254` (cloud metadata service), or `10.x.x.x` inside a VPC. Pin the URL to a hard-coded value in the test, or run it through an allowlist before passing it in.

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
- `one_of(actual, options, *, case_sensitive=False)`: exact equality against a list of alternatives. Use for deterministic varying replies such as `["yes", "yeah", "yep"]`.

Use these matchers when a plain `assert "hello" in convo.last.bot` would give noisy failure output across many tests. For one-off checks, plain `assert` is still fine.

## Fixtures

| Fixture | Purpose |
| --- | --- |
| `conversation` | Empty Conversation, no adapter. Good for user-only flows where the test drives both sides. |
| `conversation_factory` | Builder. Pass a bot callable plus optional `state`, get a fresh Conversation per call. |

## Public API

- `Conversation(bot=None, turns=[], state={})`
- `Conversation.say(text)`: drive a turn through the adapter, return the Turn.
- `Conversation.add_user(text)`: append a user-only turn without calling the adapter.
- `Conversation.last`, `.turns`, `.history`, `.transcript()`.
- `Turn(user, bot, metadata)`.
- `BotAdapter = Callable[[str, Conversation], str]`.
- `expect.contains`, `expect.regex`, `expect.one_of`.
- `pytest_conversational.adapters.http_webhook(url, *, timeout, request_builder, response_parser, max_reply_bytes)`.

## Limitations and known gaps

- **No async adapters yet:** the adapter contract is synchronous. Coroutine-based bots will be supported in v0.5; for now wrap them in `asyncio.run` inside the adapter.
- **No scenario DSL yet:** scripted multi-turn scenarios from YAML or plain text fixtures are on the v0.4 roadmap. Today the plugin keeps the runtime side; scenario loading is on the caller.
- **HTTP webhook is the only bundled adapter:** any other transport (WebSocket, Telegram Bot API, Twilio, etc.) needs a small custom callable. The contract is one function with signature `(text: str, convo: Conversation) -> str`.
- **Status: alpha.** API surface is stable for the documented Public API list above; internal helpers may move between minor versions until v1.0 (target 12.06.2026).

## References

- Project README and design notes: https://github.com/golikovichev/pytest-conversational
- PyPI package: https://pypi.org/project/pytest-conversational/
- Changelog: https://github.com/golikovichev/pytest-conversational/blob/main/CHANGELOG.md
