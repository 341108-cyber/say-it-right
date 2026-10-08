"""Role-play scenarios. Every person and situation is fictional."""

SCENARIOS = [
    {
        "id": "career", "emoji": "🏠", "title": "Tell your parents you're switching careers",
        "who": "Papa", "role": "Your father, 54",
        "personality": "Loving but worried. Paid for your engineering degree, values a stable job, fears you are throwing it away. "
                       "Softens when he hears a concrete plan and respect for his sacrifices; gets more anxious with vague dreams.",
        "situation": "You work in an IT job and want to leave it for a 1-year UX design course.",
        "goal": "Get his agreement to let you try the design course for one year",
        "opening": "Beta, your mother said you wanted to talk about something important. Is everything okay at work?",
        "start": 35,
    },
    {
        "id": "raise", "emoji": "💼", "title": "Ask your manager for a raise",
        "who": "Neha", "role": "Your manager",
        "personality": "Busy, fair and budget-conscious. Responds well to evidence of impact and a specific ask; "
                       "pushes back on complaints about workload or comparisons with colleagues.",
        "situation": "You've been in the role 18 months, led a project that cut report time by 30%, and haven't had a raise.",
        "goal": "Get her to agree to review your pay this quarter",
        "opening": "Hi! You wanted 15 minutes? I've got a client call right after, so let's make it quick.",
        "start": 45,
    },
    {
        "id": "no", "emoji": "🙅", "title": "Say no to extra weekend work",
        "who": "Rohit", "role": "Your team lead",
        "personality": "Friendly but pushy under deadline pressure. Accepts a firm no if you offer an alternative; "
                       "pushes harder if you sound unsure or over-apologise.",
        "situation": "It's Friday evening. You have a family function this weekend that was planned weeks ago.",
        "goal": "Decline the weekend task without damaging the relationship",
        "opening": "Hey, quick one. Can you take over the Q3 client deck this weekend? They moved the deadline up.",
        "start": 50,
    },
    {
        "id": "apology", "emoji": "💛", "title": "Apologise to a friend you let down",
        "who": "Ananya", "role": "Your close friend",
        "personality": "Hurt, not angry. You cancelled on her birthday dinner an hour before. Opens up to a genuine apology "
                       "with no excuses; closes off if you justify yourself or make it about you.",
        "situation": "You cancelled her birthday dinner last minute last week and haven't really talked since.",
        "goal": "Repair the friendship and make a real plan to meet",
        "opening": "Oh. Hi. I wasn't sure you'd call.",
        "start": 25,
    },
    {
        "id": "feedback", "emoji": "🗣️", "title": "Give feedback to a teammate who's slipping",
        "who": "Karan", "role": "Your teammate",
        "personality": "Defensive at first and secretly overloaded. Opens up if you describe specific behaviour and ask about him; "
                       "shuts down if you blame or generalise (\"you always...\").",
        "situation": "Karan missed two deadlines on your shared project, and you had to cover for him with the client.",
        "goal": "Agree on a concrete fix for the missed deadlines without a fight",
        "opening": "Yeah? You said you wanted to talk about the project?",
        "start": 45,
    },
]

BY_ID = {s["id"]: s for s in SCENARIOS}


def custom_scenario(who, situation, goal):
    return {
        "id": "custom", "emoji": "✨", "title": "Your own conversation",
        "who": who.split(",")[0].strip()[:30] or "Them", "role": who.strip()[:80],
        "personality": "Behave like a realistic person in this situation: not a pushover, not hostile. "
                       "Soften when the user is clear, respectful and specific.",
        "situation": situation.strip()[:600], "goal": goal.strip()[:200],
        "opening": "", "start": 45,
    }
