"""FAQ bot example.

Shows how to use ``expect.one_of`` and ``expect.regex`` against a bot that
returns canned answers based on keywords in the user message.
"""

from pytest_conversational import expect


def faq_bot(text, convo):
    text = text.lower()
    if "hi" in text or "hello" in text:
        return "Hello! How can I help you today?"
    if "hours" in text:
        return "We are open 9am-5pm, Monday to Friday."
    if "refund" in text:
        return "Refunds take 5-7 business days to process."
    return "I'm sorry, I don't have an answer for that."


def test_greeting_variants(conversation_factory):
    convo = conversation_factory(bot=faq_bot)

    convo.say("Hi there")
    expect.one_of(convo.last.bot, ["Hello! How can I help you today?", "Hi!"])


def test_store_hours(conversation_factory):
    convo = conversation_factory(bot=faq_bot)

    convo.say("What are your hours?")
    expect.regex(convo.last.bot, r"\d[ap]m-\d[ap]m")
    expect.contains(convo.last.bot, "Monday")
