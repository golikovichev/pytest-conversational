"""Allure attachment helpers for Conversation transcripts.

Two public helpers serialize a Conversation into formats Allure understands,
and a third helper performs the best-effort attach with graceful fallback
when allure-pytest is not installed.

The module has no hard dependency on allure-pytest: the import is local
to attach_to_allure, so users without Allure pay no cost.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_conversational.conversation import Conversation


# Default bounds for transcript attachments. A long-running conversation with
# thousands of turns or huge bot replies otherwise produces multi-MB Allure
# attachments that can overwhelm the Allure UI or hit backend size limits.
# Both serialise/render helpers accept overrides so a project can tune them.
MAX_TURNS_PER_ATTACHMENT = 500
MAX_CHARS_PER_FIELD = 10000

_TILDE_RUN = re.compile(r"~+")


def _cap_chars(text: str, max_chars: int) -> tuple[str, int | None]:
    """Truncate ``text`` to ``max_chars``. Returns ``(text, original_len)``;
    ``original_len`` is ``None`` when no truncation happened. A ``max_chars``
    of ``0`` or less means unlimited (no truncation)."""
    if max_chars <= 0 or len(text) <= max_chars:
        return text, None
    return text[:max_chars], len(text)


def _fence(content: str) -> str:
    """Wrap user-controlled content in a tilde code fence so backticks,
    headings, or HTML in the payload cannot break out of the turn structure
    in the Allure Markdown renderer. The fence is made longer than the
    longest tilde run inside the content so nested fences cannot escape."""
    longest = max((len(m.group()) for m in _TILDE_RUN.finditer(content)), default=0)
    fence = "~" * max(3, longest + 1)
    return f"{fence}text\n{content}\n{fence}"


def serialize_transcript_json(
    conversation: "Conversation",
    max_turns: int = MAX_TURNS_PER_ATTACHMENT,
    max_chars: int = MAX_CHARS_PER_FIELD,
) -> str:
    """Return a JSON string describing the conversation.

    Layout::

        {
          "turns": [{"user": "...", "bot": "...", "metadata": {...}}, ...],
          "state": {...},
          "truncated_turns": N   # only present when the turn cap was hit
        }

    Turns past ``max_turns`` are dropped and the original count is recorded
    under ``truncated_turns``. Each text field is capped at ``max_chars`` so
    a single huge reply cannot blow up the attachment. JSON is indented and
    uses ``ensure_ascii=False`` so non-ASCII bot replies stay readable.
    """
    total = len(conversation.turns)
    if max_turns <= 0:  # symmetry with max_chars: <= 0 means unlimited
        max_turns = total
    kept = conversation.turns[:max_turns]

    def _field(value: str) -> str:
        capped, original = _cap_chars(value, max_chars)
        if original is None:
            return capped
        return f"{capped}[truncated, original chars: {original}]"

    def _meta(value: object) -> object:
        # Cap long string values so a huge metadata field cannot blow up the
        # attachment. Non-string values are kept raw so the JSON round-trips.
        return _field(value) if isinstance(value, str) else value

    payload: dict = {
        "turns": [
            {
                "user": _field(t.user),
                "bot": _field(t.bot),
                "metadata": {k: _meta(v) for k, v in t.metadata.items()},
            }
            for t in kept
        ],
        "state": dict(conversation.state),
    }
    if total > max_turns:
        payload["truncated_turns"] = total
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _append_fenced_field(
    lines: list[str], label: str, value: str, max_chars: int
) -> None:
    """Append a ``**LABEL:**`` heading followed by the value inside a tilde
    code fence, with a truncation marker when the value was capped."""
    capped, original = _cap_chars(value, max_chars)
    lines.append(f"**{label}:**")
    lines.append(_fence(capped))
    if original is not None:
        lines.append(f"[truncated, original chars: {original}]")
    lines.append("")


def render_transcript_markdown(
    conversation: "Conversation",
    max_turns: int = MAX_TURNS_PER_ATTACHMENT,
    max_chars: int = MAX_CHARS_PER_FIELD,
) -> str:
    """Return a human-readable Markdown rendering of the conversation.

    Format mirrors how a reviewer would skim a chat log: numbered turns,
    user on top, bot below, metadata listed when present, then a State
    section if any keys were set.

    User and bot text is wrapped in tilde code fences so backticks,
    headings, or HTML in the payload render as text and cannot break out of
    the turn structure. Turns past ``max_turns`` are dropped with a
    ``[truncated, original turns: N]`` marker, and each field is capped at
    ``max_chars`` with a ``[truncated, original chars: M]`` marker.
    """
    lines: list[str] = ["# Conversation transcript", ""]

    if not conversation.turns:
        lines.append("_(empty conversation, no turns recorded)_")
        return "\n".join(lines)

    total = len(conversation.turns)
    if max_turns <= 0:  # symmetry with max_chars: <= 0 means unlimited
        max_turns = total
    for idx, turn in enumerate(conversation.turns[:max_turns], start=1):
        lines.append(f"## Turn {idx}")
        lines.append("")
        _append_fenced_field(lines, "USER", turn.user, max_chars)
        if turn.bot:
            _append_fenced_field(lines, "BOT", turn.bot, max_chars)
        else:
            lines.append("_(bot reply missing, turn incomplete)_")
            lines.append("")
        if turn.metadata:
            lines.append("Metadata:")
            for key, value in turn.metadata.items():
                capped, original = _cap_chars(repr(value), max_chars)
                marker = (
                    f" [truncated, original chars: {original}]"
                    if original is not None
                    else ""
                )
                lines.append(f"- `{key}`: {capped}{marker}")
            lines.append("")

    if total > max_turns:
        lines.append(f"[truncated, original turns: {total}]")
        lines.append("")

    if conversation.state:
        lines.append("## State")
        lines.append("")
        for key, value in conversation.state.items():
            lines.append(f"- `{key}`: {value!r}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def attach_to_allure(
    conversation: "Conversation",
    label: str = "conversation",
    max_turns: int = MAX_TURNS_PER_ATTACHMENT,
    max_chars: int = MAX_CHARS_PER_FIELD,
) -> bool:
    """Attach JSON and Markdown transcripts to the current Allure report.

    Returns True if the attach succeeded, False otherwise. Failure paths:
    allure-pytest is not installed, or the allure module raised an error
    (for example because no Allure context is active). Both are swallowed
    so that the caller never has to handle them: the fixture and hook
    layers treat attach as best-effort.

    The label is used as a prefix for the attachment filenames so that
    multiple Conversation fixtures in the same test do not collide.
    """
    try:
        import allure  # type: ignore[import-not-found]
    except ImportError:
        return False

    try:
        allure.attach(
            serialize_transcript_json(conversation, max_turns, max_chars),
            name=f"{label}.json",
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            render_transcript_markdown(conversation, max_turns, max_chars),
            name=f"{label}.md",
            attachment_type=allure.attachment_type.MARKDOWN,
        )
        return True
    except Exception:
        return False
