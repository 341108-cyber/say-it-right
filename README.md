# 💬 Say It Right

Rehearse the conversations you keep putting off. Use case **#15 Language/soft-skills practice bot (Chatbot)**.

An AI plays the other person (a worried parent, a busy manager, a hurt friend) while a private coach comments on your
tone and wording. An **openness meter** shows how the other person is feeling, and a debrief scores five skills.
Progress is saved across sessions in a bookmarkable link.

| Brief requirement | How it's built |
|---|---|
| Conversational role-play scenarios | 5 built-in scenarios plus your own custom scenario |
| Grammar/tone feedback | Tone tag, coach tip and grammar fix under every message; debrief with 5 skill scores and rewrites |
| Progress tracking over sessions | Sessions saved in the page link (and downloadable); score chart and goals reached on the home screen |

**Files:** `app.py` · `prompts.py` · `scenarios.py` · `progress.py` · `llm_client.py`

## Deploy
1. Free Groq key: https://console.groq.com/keys
2. Upload the files to a public GitHub repo (check the `.streamlit` folder uploaded).
3. https://share.streamlit.io → Create app → `app.py` → Advanced settings → Secrets: `GROQ_API_KEY = "gsk_..."`
4. Deploy and share the link.
