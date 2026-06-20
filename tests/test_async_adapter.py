"""Async bot adapter wiring: say_async() awaits a coroutine adapter and
records the reply, mirroring the synchronous say() contract. The sync say()
must refuse an async adapter with a clear error instead of silently storing
an un-awaited coroutine as the reply.

These tests drive the coroutines with asyncio.run() so the suite needs no
extra async plugin, keeping the package's zero-dependency stance.
"""

import asyncio
import warnings

import pytest

from pytest_conversational import Conversation


async def echo_bot(text: str, convo: Conversation) -> str:
    return f"echo: {text}"


def test_say_async_awaits_adapter_and_records_reply():
    convo = Conversation(bot=echo_bot)
    turn = asyncio.run(convo.say_async("ping"))
    assert turn.user == "ping"
    assert turn.bot == "echo: ping"
    assert convo.last is turn


def test_say_async_appends_in_order():
    async def drive():
        convo = Conversation(bot=echo_bot)
        await convo.say_async("one")
        await convo.say_async("two")
        await convo.say_async("three")
        return convo

    convo = asyncio.run(drive())
    assert [t.user for t in convo.turns] == ["one", "two", "three"]
    assert [t.bot for t in convo.turns] == ["echo: one", "echo: two", "echo: three"]


def test_say_async_without_adapter_raises():
    convo = Conversation()
    with pytest.raises(RuntimeError, match="no bot adapter"):
        asyncio.run(convo.say_async("hello"))


def test_say_async_adapter_can_await_and_read_state():
    async def slot_bot(text: str, convo: Conversation) -> str:
        await asyncio.sleep(0)  # a real coroutine yields control
        slots = convo.state.setdefault("slots", {})
        if "name" not in slots:
            slots["name"] = text
            return "got it, what city?"
        slots["city"] = text
        return f"hello {slots['name']} from {slots['city']}"

    async def drive():
        convo = Conversation(bot=slot_bot)
        await convo.say_async("Mikhail")
        await convo.say_async("Hove")
        return convo

    convo = asyncio.run(drive())
    assert convo.state["slots"] == {"name": "Mikhail", "city": "Hove"}
    assert convo.last.bot == "hello Mikhail from Hove"


def test_say_async_adapter_exception_propagates_and_partial_turn_stays():
    async def angry_bot(text: str, convo: Conversation) -> str:
        raise ValueError("upstream broke")

    convo = Conversation(bot=angry_bot)
    with pytest.raises(ValueError, match="upstream broke"):
        asyncio.run(convo.say_async("hello"))
    assert len(convo.turns) == 1
    assert convo.turns[0].user == "hello"
    assert convo.turns[0].bot == ""


def test_sync_say_on_async_adapter_raises_clear_error_without_warning():
    """The whole point: an async adapter passed to the sync say() must fail
    loudly, not silently store a coroutine object in turn.bot. And it must
    not leak a 'coroutine was never awaited' RuntimeWarning."""
    convo = Conversation(bot=echo_bot)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any RuntimeWarning becomes an error
        with pytest.raises(TypeError, match="say_async"):
            convo.say("ping")
    # no partial turn with a coroutine reply should linger
    assert convo.last is None or convo.last.bot == ""
