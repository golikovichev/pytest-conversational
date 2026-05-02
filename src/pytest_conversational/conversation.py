"""Core Conversation and Turn data models. State tracking added in Sess 3."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Turn:
    """A single user input plus the bot reply."""

    user: str
    bot: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Container for an ordered list of Turns. Stub for Sess 2."""

    turns: list[Turn] = field(default_factory=list)

    def add_user(self, text: str) -> Turn:
        turn = Turn(user=text)
        self.turns.append(turn)
        return turn

    @property
    def last(self) -> Turn | None:
        return self.turns[-1] if self.turns else None
