# pytest-conversational reference

Detailed Public API, matchers, fixtures, and adapter contract. SKILL.md keeps the quick-start and a single multi-turn example. Read this file when you need the full surface.

## Public API surface

### `Conversation`

```python
Conversation(bot=None, turns=[], state={})
```

- `bot`: optional `BotAdapter` callable. Required for `say()`; not required for user-only flows.
- `turns`: list of `Turn` objects. Usually starts empty; the plugin appends as the test drives turns.
- `state`: dict for per-conversation memory the adapter can read and write across turns.

#### Methods

- `Conversation.say(text) -> Turn`: drive a turn through the adapter. Appends a `Turn(user=text)` first so the adapter sees the in-progress turn in `convo.history`, then writes the reply back into the same Turn on success. Raises whatever the adapter raises; the partial Turn stays in `turns` with `turn.bot == ""` so the test can still inspect what was attempted.
- `Conversation.add_user(text) -> Turn`: append a user-only turn without calling the adapter. Useful for setting up history before a single `say()`.

#### Properties

- `Conversation.last`: the most recent Turn, or `None` if empty.
- `Conversation.turns`: full list of Turn objects, in order.
- `Conversation.history`: list of `(user, bot)` tuples. Read-only view convenient for matchers.
- `Conversation.transcript() -> str`: plain-text rendering of the dialogue. Used in failure messages.

### `Turn`

```python
@dataclass
class Turn:
    user: str
    bot: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
```

`metadata` is per-turn (intent label, slot extraction, latency). Cross-turn state lives on `Conversation.state`.

### `BotAdapter` type alias

```python
BotAdapter = Callable[[str, Conversation], str]
```

A bot adapter is any callable that takes user text plus the current conversation and returns the bot reply.

## Matchers

`pytest_conversational.expect` is a small module of assertion helpers tuned for bot replies. Each matcher raises `AssertionError` with the actual reply embedded in the message, so pytest output shows what the bot said versus what the test wanted.

### Reply matchers

- `contains(actual: str, substring: str, *, case_sensitive: bool = False) -> None`
  Substring search. Case-insensitive by default. Raises if `actual` is `None` or does not contain `substring`.

- `regex(actual: str, pattern: str, *, flags: int = 0) -> re.Match[str]`
  `re.search` semantics. Returns the match object so callers can inspect captured groups. Raises if `actual` is `None` or the pattern does not match.

- `one_of(actual: str, options: Iterable[str], *, case_sensitive: bool = False, mode: str = "exact") -> None`
  Asserts `actual` matches one of `options`. Modes: `"exact"` (default) for full-string equality, `"substring"` for substring match. Use for deterministic varying replies like `["yes", "yeah", "yep"]`. Raises if `options` is empty, `mode` is invalid, `actual` is `None`, or no option matches.

### Metadata matchers

These read fields the adapter records on `turn.metadata` or `convo.state`.

- `has_intent(turn, intent_name)`: asserts `turn.metadata["intent"] == intent_name`. Fails clearly if no intent was recorded.
- `has_slot(turn, slot_name, value=UNSET)`: asserts a slot is present in `turn.metadata["slots"]`. Pass `value=` for equality. Distinguishes "slot missing" from "slot set to wrong value" in the failure message.
- `has_state(convo, state_name, value=UNSET)`: same shape but for `convo.state` (conversation-wide, not per-turn).
- `responds_within(turn, seconds)`: asserts `turn.metadata["latency_ms"]` is within the budget. Adapters that measure latency record it in milliseconds; the budget is in seconds for readability. Raises `ValueError` for a negative budget.

## Fixtures

| Fixture | Purpose |
| --- | --- |
| `conversation` | Empty Conversation, no adapter. Good for user-only flows where the test drives both sides. |
| `conversation_factory` | Builder. Pass a bot callable plus optional `state`, get a fresh Conversation per call. |

The `conversational` marker is registered as well, so tests opted into multi-turn flow can be filtered with `pytest -m conversational`.

## HTTP webhook adapter

```python
from pytest_conversational.adapters import http_webhook

bot = http_webhook(
    url,
    *,
    timeout=5.0,
    request_builder=None,
    response_parser=None,
    max_reply_bytes=1_048_576,
    allowed_hosts=None,
)
```

### Default contract

- Request: `POST <url>` with JSON body `{"user": text, "history": [[u, b], ...]}`
- Response: `200 OK` with JSON `{"reply": "..."}`

### Overrides

- `request_builder(text, convo) -> dict`: build a custom JSON payload. Default builder packs `user` + `history`.
- `response_parser(response) -> str`: extract the reply string from `httpx.Response`. Default reads `response.json()["reply"]`.
- `max_reply_bytes`: hard cap before JSON parse. Larger responses raise before allocation. Default 1 MiB.
- `allowed_hosts`: optional iterable of permitted hostnames. When set, the URL host must match one entry exactly (case-insensitive) or the adapter constructor raises `ValueError` before any HTTP traffic.

### Security: webhook reply is data, not instructions

This adapter is a test harness, not an agent driver. The reply string is captured as test output and asserted against by user-written matchers (`expect.contains`, `assert convo.last.bot == ...`). Nothing in the plugin interprets the reply as an instruction. That said, two threats are worth pinning down explicitly:

**Host control.** The URL is passed to `httpx` unchanged. If a test reads the URL from fixture data, an env file, or any other source the developer does not control end-to-end, the adapter will happily hit it, including `127.0.0.1`, `169.254.169.254` (cloud metadata service), or VPC-internal addresses. Pin the host explicitly:

```python
bot = http_webhook(
    os.environ["BOT_URL"],
    allowed_hosts=["staging-bot.example.com"],
)
```

Adapter construction raises `ValueError` immediately if the URL host is not in the list. Case-insensitive match on the hostname only; ports, paths, and embedded credentials (`user:pass@host` form) are not part of the check. Trailing FQDN-root dots (`bot.test.`) are treated as equivalent to the bare form (`bot.test`). The same allowlist also catches IPv6 loopback (`http://[::1]/...`) and link-local addresses (`fe80::/10`), since `urlparse` returns the bare IPv6 string for the hostname.

The URL must include an explicit scheme (`http://` or `https://`). A scheme-less URL such as `bot.test/webhook` raises a specific `has no scheme` error rather than the generic host-mismatch message, so a typo in an env var fails clearly.

**Reply content trust.** The matchers (`expect.contains`, `expect.regex`, etc.) treat the reply as a string for assertions. If your test logs or persists replies elsewhere (for example to a CI test report consumed by a downstream tool), you may want to sanitise. The bundled matchers themselves do not eval, exec, render Markdown, or otherwise interpret the reply.

### Optional install

```bash
pip install 'pytest-conversational[http]'
```

The base install does not require `httpx`. Importing `pytest_conversational.adapters.http_webhook` without the extra fails with a helpful `ImportError` only when the adapter is actually called.

## Error handling reference

- **Adapter raised an exception:** the exception propagates unchanged through `convo.say()`. Tests can pattern-match on the concrete type (`pytest.raises(MyAdapterError)`). The partial Turn stays in `convo.turns`.
- **Webhook timeout:** `httpx.TimeoutException` propagates. Adjust `timeout=` per call.
- **Webhook body too large:** raises before JSON parse with a clear message.
- **Webhook returned non-200:** `httpx.HTTPStatusError`.
- **Wrong reply shape:** `KeyError` or `TypeError` if the default parser cannot find `reply`. Pass `response_parser` to handle a different shape.

## External links

- Project README and design notes: https://github.com/golikovichev/pytest-conversational
- PyPI package: https://pypi.org/project/pytest-conversational/
- Changelog: https://github.com/golikovichev/pytest-conversational/blob/main/CHANGELOG.md
