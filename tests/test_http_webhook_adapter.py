"""Tests for the HTTP webhook adapter using httpx.MockTransport."""

import json

import httpx
import pytest

from pytest_conversational import Conversation
from pytest_conversational.adapters import http_webhook


def _client_with_handler(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_default_request_shape_and_reply_parsing():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"reply": "pong"})

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/webhook", client=client)
        convo = Conversation(bot=bot)
        turn = convo.say("ping")

    assert turn.bot == "pong"
    assert captured["url"] == "https://bot.test/webhook"
    assert captured["body"] == {"user": "ping", "history": [["ping", ""]]}


def test_history_is_sent_on_subsequent_turns():
    sent_histories = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_histories.append(json.loads(request.content)["history"])
        return httpx.Response(200, json={"reply": "ok"})

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/x", client=client)
        convo = Conversation(bot=bot)
        convo.say("first")
        convo.say("second")

    assert sent_histories[0] == [["first", ""]]
    assert sent_histories[1] == [["first", "ok"], ["second", ""]]


def test_non_2xx_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/x", client=client)
        convo = Conversation(bot=bot)
        with pytest.raises(httpx.HTTPStatusError):
            convo.say("hello")


def test_missing_reply_field_raises_value_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "wrong shape"})

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/x", client=client)
        convo = Conversation(bot=bot)
        with pytest.raises(ValueError, match="missing 'reply'"):
            convo.say("hi")


def test_non_string_reply_raises_value_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"reply": 42})

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/x", client=client)
        convo = Conversation(bot=bot)
        with pytest.raises(ValueError, match="must be a string"):
            convo.say("hi")


def test_custom_request_builder_replaces_payload():
    captured_bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"reply": "k"})

    def build(text, convo):
        return {"text": text, "session_id": convo.state.get("sid", "anon")}

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/x", client=client, request_builder=build)
        convo = Conversation(bot=bot)
        convo.state["sid"] = "abc-123"
        convo.say("yo")

    assert captured_bodies[0] == {"text": "yo", "session_id": "abc-123"}


def test_custom_response_parser_reads_other_field():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"answer": "42"}})

    def parse(response):
        response.raise_for_status()
        return response.json()["data"]["answer"]

    with _client_with_handler(handler) as client:
        bot = http_webhook("https://bot.test/x", client=client, response_parser=parse)
        convo = Conversation(bot=bot)
        convo.say("life?")

    assert convo.last.bot == "42"


def test_headers_are_merged_into_request():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["x-token"] = request.headers.get("x-token")
        return httpx.Response(200, json={"reply": "hi"})

    with _client_with_handler(handler) as client:
        bot = http_webhook(
            "https://bot.test/x",
            client=client,
            headers={"X-Token": "secret"},
        )
        convo = Conversation(bot=bot)
        convo.say("ping")

    assert seen_headers["x-token"] == "secret"


def test_adapter_works_without_explicit_client(monkeypatch):
    """Sanity check: when no client is passed, http_webhook builds one. We patch
    httpx.Client so we don't make a real network call."""

    calls = {"posted": 0}

    class FakeResponse:
        status_code = 200
        # Default parser checks len(response.content) against max_reply_bytes
        # before parsing JSON; the fake needs a bytes-like content attribute.
        content = b'{"reply": "ack"}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"reply": "ack"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            calls["timeout"] = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, json, headers):
            calls["posted"] += 1
            calls["url"] = url
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    bot = http_webhook("https://bot.test/x", timeout=2.0)
    convo = Conversation(bot=bot)
    convo.say("hi")

    assert calls["posted"] == 1
    assert calls["url"] == "https://bot.test/x"
    assert calls["timeout"] == 2.0
    assert convo.last.bot == "ack"


# M4: reply size guard (added 2026-05-20)


def test_reply_size_guard_rejects_oversized_response_body():
    """Default parser refuses a response whose raw bytes exceed max_reply_bytes,
    even if the JSON would have parsed successfully."""
    huge_padding = "x" * 2048  # makes the JSON body > 1024 bytes

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"reply": "ok", "padding": huge_padding})

    with _client_with_handler(handler) as client:
        bot = http_webhook(
            "https://bot.test/webhook", client=client, max_reply_bytes=1024
        )
        convo = Conversation(bot=bot)
        with pytest.raises(ValueError, match=r"response body exceeds max_reply_bytes"):
            convo.say("ping")


def test_reply_size_guard_allows_payload_under_limit():
    """Normal-sized response passes through cleanly with the guard armed."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"reply": "tiny"})

    with _client_with_handler(handler) as client:
        bot = http_webhook(
            "https://bot.test/webhook", client=client, max_reply_bytes=1024
        )
        convo = Conversation(bot=bot)
        turn = convo.say("ping")
    assert turn.bot == "tiny"


def test_custom_response_parser_bypasses_size_guard():
    """When the caller supplies their own response_parser, the default
    size guard is not in play, the custom parser owns its limits."""
    huge_reply = "z" * 10000

    def custom_parser(response: httpx.Response) -> str:
        # Custom parser deliberately ignores size, returns whatever came back.
        return response.json()["reply"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"reply": huge_reply})

    with _client_with_handler(handler) as client:
        bot = http_webhook(
            "https://bot.test/webhook",
            client=client,
            response_parser=custom_parser,
            max_reply_bytes=100,  # would have blocked default parser, but ignored here
        )
        convo = Conversation(bot=bot)
        turn = convo.say("ping")
    assert turn.bot == huge_reply
