# pytest-conversational Examples

This directory contains example bots and tests demonstrating how to use `pytest-conversational` to verify different conversational flows.

* **[`test_faq_bot.py`](test_faq_bot.py)**: Demonstrates testing a simple rule-based bot that handles standard keyword queries (greetings, hours, refunds).
* **[`test_order_bot.py`](test_order_bot.py)**: Shows how to test a bot that extracts specific data formats (like order IDs) using regular expressions.
* **[`test_weather_bot.py`](test_weather_bot.py)**: Illustrates testing a multi-turn conversation where the bot remembers state from previous turns to ask follow-up questions.

