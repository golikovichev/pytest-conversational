"""Conversation and Turn models with bot adapter wiring."""

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

BotAdapter = Callable[[str, "Conversation"], str]
"""Callable that takes the user text plus the current conversation and returns the bot reply."""

AsyncBotAdapter = Callable[[str, "Conversation"], Awaitable[str]]
"""Coroutine adapter: same shape as BotAdapter but returns an awaitable reply. Drive it with ``say_async``."""


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

        The Turn is appended to ``self.turns`` BEFORE the adapter call so
        the adapter sees the in-progress turn through ``convo.history``
        (the default request builder relies on this contract). The reply
        is written back into the same Turn object on success.

        Partial-transcript semantics: if the adapter raises, the partial
        Turn stays in ``self.turns`` with ``turn.bot == ""`` and the
        original exception propagates to the caller unchanged. Callers
        can inspect ``convo.turns[-1]`` to see what was attempted before
        the failure, while still pattern-matching on the original
        exception type (``httpx.HTTPStatusError``, ``ValueError``, etc.).

        Raises:
            RuntimeError: if no adapter is attached.
            Exception: whatever the adapter itself raises, propagated as-is.
        """
        if self.bot is None:
            raise RuntimeError(
                "Conversation has no bot adapter. "
                "Pass bot=callable when constructing, or use add_user for user-only flows."
            )
        turn = Turn(user=text)
        self.turns.append(turn)
        reply = self.bot(text, self)
        if inspect.isawaitable(reply):
            # An async adapter was passed to the synchronous path. Storing the
            # coroutine in turn.bot would silently corrupt the transcript and
            # leak a "coroutine was never awaited" RuntimeWarning, so refuse
            # loudly and undo the partial turn instead.
            if inspect.iscoroutine(reply):
                reply.close()
            self.turns.remove(turn)
            raise TypeError(
                "Bot adapter returned an awaitable. Use 'await convo.say_async(...)' "
                "for coroutine bots; say() only drives synchronous adapters."
            )
        turn.bot = reply
        return turn

    async def say_async(self, text: str) -> Turn:
        """Async counterpart of ``say`` for coroutine bot adapters.

        Awaits the adapter's reply and writes it back into the same Turn.
        Turn ordering, the ``convo.history`` contract, and partial-transcript
        semantics on failure match ``say`` exactly: a raising adapter leaves
        the partial Turn (``turn.bot == ""``) in ``self.turns`` and propagates
        the original exception unchanged.

        Raises:
            RuntimeError: if no adapter is attached.
            Exception: whatever the adapter itself raises, propagated as-is.
        """
        if self.bot is None:
            raise RuntimeError(
                "Conversation has no bot adapter. "
                "Pass bot=callable when constructing, or use add_user for user-only flows."
            )
        turn = Turn(user=text)
        self.turns.append(turn)
        turn.bot = await self.bot(text, self)
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
