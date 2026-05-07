"""Conversation and Turn models with bot adapter wiring."""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

BotAdapter = Callable[[str, "Conversation"], str]
"""Callable that takes the user text plus the current conversation and returns the bot reply."""


@dataclass
class Turn:
    """One round of user input plus the bot reply.

    Metadata is per-turn (intent, slot extraction, latency). State that
    persists across turns lives on Conversation.state.
    """

    user: str
    bot: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Ordered list of Turns plus a shared state bag.

    A bot adapter is optional. Without one, ``add_user`` keeps the legacy
    behaviour and records only the user side. With an adapter, ``say``
    drives a full round and writes the reply back into the same turn.
    """

    turns: list[Turn] = field(default_factory=list)
    bot: Optional[BotAdapter] = None
    state: dict[str, Any] = field(default_factory=dict)

    def add_user(self, text: str) -> Turn:
        """Append a user-only turn. No adapter is called."""
        turn = Turn(user=text)
        self.turns.append(turn)
        return turn

    def say(self, text: str) -> Turn:
        """Send user text through the bot adapter and record the reply.

        Raises RuntimeError if no adapter was attached. The same Turn
        object is returned so callers can read ``turn.bot`` or stash
        custom values into ``turn.metadata``.
        """
        if self.bot is None:
            raise RuntimeError(
                "Conversation has no bot adapter. "
                "Pass bot=callable when constructing, or use add_user for user-only flows."
            )
        turn = Turn(user=text)
        self.turns.append(turn)
        reply = self.bot(text, self)
        turn.bot = reply
        return turn

    @property
    def last(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    @property
    def history(self) -> list[tuple[str, str]]:
        """List of (user, bot) tuples in turn order. Read-only view for assertions."""
        return [(t.user, t.bot) for t in self.turns]

    def transcript(self) -> str:
        """Plain-text rendering of the dialogue. Useful in failure messages."""
        lines = []
        for t in self.turns:
            lines.append(f"USER: {t.user}")
            if t.bot:
                lines.append(f"BOT:  {t.bot}")
        return "\n".join(lines)
