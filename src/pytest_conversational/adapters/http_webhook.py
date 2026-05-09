"""HTTP webhook bot adapter.

Wraps an HTTP endpoint as a BotAdapter callable. The default contract is:

    POST {url}
    Content-Type: application/json
    Body:    {"user": "...", "history": [["user1", "bot1"], ...]}
    Reply:   200 OK, JSON body with a "reply" string field.

Bots that speak a different shape can pass ``request_builder`` and
``response_parser`` callbacks to translate at the edges without forking
the adapter.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

try:
    import httpx
except ImportError as exc:
    raise ImportError(
        "http_webhook requires httpx. Install with: pip install pytest-conversational[http]"
    ) from exc

from pytest_conversational.conversation import BotAdapter, Conversation

RequestBuilder = Callable[[str, Conversation], dict[str, Any]]
ResponseParser = Callable[[httpx.Response], str]


def _default_request(text: str, convo: Conversation) -> dict[str, Any]:
    return {"user": text, "history": [list(pair) for pair in convo.history]}


def _default_parse(response: httpx.Response) -> str:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or "reply" not in payload:
        raise ValueError(
            f"Webhook response missing 'reply' field. Got: {payload!r}"
        )
    reply = payload["reply"]
    if not isinstance(reply, str):
        raise ValueError(f"Webhook 'reply' must be a string, got {type(reply).__name__}")
    return reply


def http_webhook(
    url: str,
    *,
    timeout: float = 5.0,
    headers: Optional[dict[str, str]] = None,
    request_builder: Optional[RequestBuilder] = None,
    response_parser: Optional[ResponseParser] = None,
    client: Optional[httpx.Client] = None,
) -> BotAdapter:
    """Build a BotAdapter that sends each user turn to an HTTP endpoint.

    Args:
        url: Webhook endpoint receiving the POST.
        timeout: Per-request timeout in seconds. Ignored when ``client`` is given.
        headers: Optional extra headers merged into every request.
        request_builder: Callback ``(text, convo) -> dict`` for the JSON body.
            Defaults to ``{"user": text, "history": [[u, b], ...]}``.
        response_parser: Callback ``(httpx.Response) -> str`` returning the reply.
            Defaults to reading ``payload["reply"]`` and raising on non-2xx.
        client: Reuse an existing ``httpx.Client`` (handy for tests with
            ``httpx.MockTransport``). When omitted, a fresh client is built
            per call so the adapter stays free of hidden state.

    Returns:
        A BotAdapter callable suitable for ``Conversation(bot=...)``.
    """
    build = request_builder or _default_request
    parse = response_parser or _default_parse

    def _adapter(text: str, convo: Conversation) -> str:
        body = build(text, convo)
        if client is not None:
            response = client.post(url, json=body, headers=headers)
        else:
            with httpx.Client(timeout=timeout) as fresh:
                response = fresh.post(url, json=body, headers=headers)
        return parse(response)

    return _adapter
