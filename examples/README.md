# Examples

Three minimal pytest-conversational examples. Clone the repo, install in
editable mode, run `pytest examples/ -v`, and you should see green dots
before reading any other documentation.

```bash
pip install -e .
pytest examples/ -v
```

## Files

- **`test_faq_bot.py`**: a keyword-driven FAQ bot. Uses `expect.one_of`
  and `expect.regex`. Read this first if you are new to the matchers.
- **`test_order_bot.py`**: an order-tracking bot with regex-based ID
  validation and a fallback help message. Uses `expect.contains`.
- **`test_weather_bot.py`**: a slot-filling bot that asks for a missing
  city, then reads the next turn as the slot value. Uses `convo.state`
  for multi-turn memory.

## Conventions

Each file is self-contained: one bot function plus one or two test
functions. No fixtures, no shared helpers, no `conftest.py` needed
beyond the package itself.

Generated tests in your own project usually pull the bot from your
codebase rather than defining it inline; the inline shape here is purely
for the example to fit in a single short file.

## CI coverage

These files are part of the project's CI run. The `examples-smoke` step
in `.github/workflows/ci.yml` runs `pytest examples/ -v` directly so a
regression in any example shows up as a distinct CI failure rather than
being mixed into the main test report.
