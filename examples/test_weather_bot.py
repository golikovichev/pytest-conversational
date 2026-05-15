from pytest_conversational import expect

def weather_bot(text, convo):
    """A bot that asks for a city if not provided in the first turn."""
    state = convo.state
    text = text.lower()
    
    if "weather" in text:
        if "in" in text:
            city = text.split("in")[-1].strip()
            state["city"] = city
            return f"The weather in {city} is sunny."
        return "Which city are you interested in?"
    
    # Check previous turns for context
    if len(convo.turns) > 1 and "Which city" in convo.turns[-2].bot:
        state["city"] = text
        return f"The weather in {text} is sunny."
        
    return "I only know about the weather. Ask me 'weather in London'."

def test_weather_flow(conversation_factory):
    convo = conversation_factory(bot=weather_bot)
    
    # Turn 1: Partial request
    convo.say("what is the weather?")
    assert "Which city" in convo.last.bot
    
    # Turn 2: Providing the slot
    convo.say("London")
    assert convo.state["city"] == "london"
    expect.contains(convo.last.bot, "sunny")
    expect.contains(convo.last.bot, "London")

def test_weather_direct(conversation_factory):
    convo = conversation_factory(bot=weather_bot)
    
    # Turn 1: Full request
    convo.say("weather in Paris")
    assert convo.state["city"] == "paris"
    expect.contains(convo.last.bot, "Paris")
