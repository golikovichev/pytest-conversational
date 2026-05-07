# pytest-conversational

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

## Roadmap

- v0.3: matchers (`expect.contains`, `expect.regex`, `expect.one_of`).
- v0.4: scenario DSL loaded from YAML or plain text fixtures.
- v0.5: async adapter support for coroutine-based bots.
- v1.0: 12.06.2026 release.

## Licence

MIT. See `LICENSE`.
