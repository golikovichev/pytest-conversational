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

from typing import Any, Callable, Iterable, Optional
from urllib.parse import urlparse

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


DEFAULT_MAX_REPLY_BYTES = (
    1024 * 1024
)  # 1 MiB. Generous for chat, fence against runaway bots.


def _default_parse(
    response: httpx.Response, *, max_reply_bytes: int = DEFAULT_MAX_REPLY_BYTES
) -> str:
    """Read the webhook response, return the reply string.

    The size guard fires before JSON parsing so a hostile or buggy server
    that returns a multi-megabyte payload never reaches ``response.json()``
    in the first place. The reply field itself necessarily fits inside
    the body envelope, so checking the body bytes is sufficient.
    """
    response.raise_for_status()
    if len(response.content) > max_reply_bytes:
        raise ValueError(
            f"Webhook response body exceeds max_reply_bytes={max_reply_bytes} "
            f"(got {len(response.content)} bytes)"
        )
    payload = response.json()
    if not isinstance(payload, dict) or "reply" not in payload:
        raise ValueError(f"Webhook response missing 'reply' field. Got: {payload!r}")
    reply = payload["reply"]
    if not isinstance(reply, str):
        raise ValueError(
            f"Webhook 'reply' must be a string, got {type(reply).__name__}"
        )
    return reply


def _check_host_allowed(url: str, allowed_hosts: Optional[Iterable[str]]) -> None:
    """Raise ``ValueError`` if the URL host is not in ``allowed_hosts``.

    Pass ``allowed_hosts=None`` to opt out (the default). When set, the
    check fires at adapter construction time so misconfigured tests fail
    early rather than reaching out to an unexpected endpoint at runtime.

    Host comparison is case-insensitive on both sides. Trailing FQDN-root
    dots (``bot.test.`` equivalent to ``bot.test``) are normalised away
    before comparison. URLs without an explicit scheme raise a separate,
    clearer error so the caller does not get a generic "host None" message.
    """
    if allowed_hosts is None:
        return
    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError(
            f"webhook URL {url!r} has no scheme; expected 'http://...' or "
            f"'https://...'. allowed_hosts is set, so the scheme is required "
            f"to determine the host reliably."
        )
    host = parsed.hostname
    normalised_host = host.rstrip(".").lower() if host else None
    allowed_set = {h.rstrip(".").lower() for h in allowed_hosts}
    if normalised_host is None or normalised_host not in allowed_set:
        raise ValueError(
            f"webhook URL host {host!r} is not in allowed_hosts "
            f"{sorted(allowed_set)!r}. Pin the host explicitly to prevent "
            f"accidental requests to internal addresses (127.0.0.1, "
            f"169.254.169.254, ::1, VPC ranges) or untrusted endpoints."
        )


def http_webhook(
    url: str,
    *,
    timeout: float = 5.0,
    headers: Optional[dict[str, str]] = None,
    request_builder: Optional[RequestBuilder] = None,
    response_parser: Optional[ResponseParser] = None,
    client: Optional[httpx.Client] = None,
    max_reply_bytes: int = DEFAULT_MAX_REPLY_BYTES,
    allowed_hosts: Optional[Iterable[str]] = None,
) -> BotAdapter:
    """Build a BotAdapter that sends each user turn to an HTTP endpoint.

    Args:
        url: Webhook endpoint receiving the POST.
        timeout: Per-request timeout in seconds. Ignored when ``client`` is given.
        headers: Optional extra headers merged into every request.
        request_builder: Callback ``(text, convo) -> dict`` for the JSON body.
            Defaults to ``{"user": text, "history": [[u, b], ...]}``.
        response_parser: Callback ``(httpx.Response) -> str`` returning the reply.
            Defaults to reading ``payload["reply"]`` and raising on non-2xx
            or when the reply exceeds ``max_reply_bytes``. A custom parser
            opts out of the size guard and owns its own limits.
        client: Reuse an existing ``httpx.Client`` (handy for tests with
            ``httpx.MockTransport``). When omitted, a fresh client is built
            per call so the adapter stays free of hidden state.
        max_reply_bytes: Cap on response and reply size, applied by the
            default parser. Defaults to 1 MiB. Ignored when ``response_parser``
            is supplied (the custom parser is responsible for its own limits).
        allowed_hosts: Optional allowlist of hostnames. When set, the URL
            host must match one entry exactly (case-insensitive) or
            adapter construction raises ``ValueError``. Use to prevent
            tests from reading URLs out of fixtures or env files and
            accidentally hitting internal addresses such as
            ``127.0.0.1``, ``169.254.169.254`` (cloud metadata), or
            VPC-internal ranges.

    Returns:
        A BotAdapter callable suitable for ``Conversation(bot=...)``.
    """
    _check_host_allowed(url, allowed_hosts)
    build = request_builder or _default_request
    if response_parser is None:
        # Bind max_reply_bytes via closure so the default parser keeps a
        # plain (response) -> str signature for ResponseParser type compat.
        def parse(resp: httpx.Response) -> str:
            return _default_parse(resp, max_reply_bytes=max_reply_bytes)
    else:
        parse = response_parser

    def _adapter(text: str, convo: Conversation) -> str:
        body = build(text, convo)
        if client is not None:
            response = client.post(url, json=body, headers=headers)
        else:
            with httpx.Client(timeout=timeout) as fresh:
                response = fresh.post(url, json=body, headers=headers)
        return parse(response)

    return _adapter
