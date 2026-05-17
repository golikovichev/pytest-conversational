"""Order-tracking bot example.

Shows ``expect.contains`` against a bot that validates an order-ID pattern
with regex and falls back to a help message when the input does not match.
"""

import re
from pytest_conversational import expect


def order_bot(text, convo):
    # Match order ID pattern: ORD-12345
    match = re.search(r"ORD-(\d{5})", text.upper())
    if match:
        order_num = match.group(1)
        return f"Order {order_num} is currently out for delivery."

    if "order" in text.lower():
        return "Please provide your order ID in the format ORD-XXXXX."

    return "I can help you track orders. Just say 'track ORD-12345'."


def test_order_tracking_success(conversation_factory):
    convo = conversation_factory(bot=order_bot)

    convo.say("Track my order ORD-99887")
    expect.contains(convo.last.bot, "99887")
    expect.contains(convo.last.bot, "delivery")


def test_order_invalid_format(conversation_factory):
    convo = conversation_factory(bot=order_bot)

    convo.say("I want to track an order")
    expect.contains(convo.last.bot, "format ORD-XXXXX")

    convo.say("My ID is 12345")  # Missing prefix
    expect.contains(convo.last.bot, "track ORD-12345")
