"""Allure attachment helpers for Conversation transcripts.

Two public helpers serialize a Conversation into formats Allure understands,
and a third helper performs the best-effort attach with graceful fallback
when allure-pytest is not installed.

The module has no hard dependency on allure-pytest: the import is local
to attach_to_allure, so users without Allure pay no cost.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_conversational.conversation import Conversation


def serialize_transcript_json(conversation: "Conversation") -> str:
    """Return a JSON string describing the conversation.

    Layout::

        {
          "turns": [{"user": "...", "bot": "...", "metadata": {...}}, ...],
          "state": {...}
        }

    JSON is indented and uses ``ensure_ascii=False`` so non-ASCII bot
    replies are readable in the Allure UI.
    """
    payload = {
        "turns": [
            {"user": t.user, "bot": t.bot, "metadata": dict(t.metadata)}
            for t in conversation.turns
        ],
        "state": dict(conversation.state),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_transcript_markdown(conversation: "Conversation") -> str:
    """Return a human-readable Markdown rendering of the conversation.

    Format mirrors how a reviewer would skim a chat log: numbered turns,
    user on top, bot below, metadata listed when present, then a State
    section if any keys were set.
    """
    lines: list[str] = ["# Conversation transcript", ""]

    if not conversation.turns:
        lines.append("_(empty conversation, no turns recorded)_")
        return "\n".join(lines)

    for idx, turn in enumerate(conversation.turns, start=1):
        lines.append(f"## Turn {idx}")
        lines.append("")
        lines.append(f"**USER:** {turn.user}")
        lines.append("")
        if turn.bot:
            lines.append(f"**BOT:** {turn.bot}")
        else:
            lines.append("_(bot reply missing, turn incomplete)_")
        if turn.metadata:
            lines.append("")
            lines.append("Metadata:")
            for key, value in turn.metadata.items():
                lines.append(f"- `{key}`: {value!r}")
        lines.append("")

    if conversation.state:
        lines.append("## State")
        lines.append("")
        for key, value in conversation.state.items():
            lines.append(f"- `{key}`: {value!r}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def attach_to_allure(conversation: "Conversation", label: str = "conversation") -> bool:
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
            serialize_transcript_json(conversation),
            name=f"{label}.json",
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            render_transcript_markdown(conversation),
            name=f"{label}.md",
            attachment_type=allure.attachment_type.MARKDOWN,
        )
        return True
    except Exception:
        return False
