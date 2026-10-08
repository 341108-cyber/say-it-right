"""
Say It Right: rehearse the conversations you keep putting off (Use case #15, Chatbot).

An AI plays the other person (a worried parent, a busy manager, a hurt friend) while a private coach
comments on your tone and wording. An "openness meter" shows how the other person is feeling.
Progress is saved across sessions in a bookmarkable link.

Run locally:  streamlit run app.py
"""

import html
import json
import os
from datetime import datetime
from statistics import mean

import streamlit as st

import progress
from llm_client import PROVIDER_NAMES, BadOutput, LLMClient, LLMError, detect_provider
from prompts import DEBRIEF_SYSTEM, SKILLS, debrief_prompt, opening_prompt, roleplay_system, turn_prompt
from scenarios import BY_ID, SCENARIOS, custom_scenario

st.set_page_config(page_title="Say It Right", page_icon="💬", layout="centered")

MAX_TURNS = 10
MAX_CHARS = 600
OPENNESS_STEP = 8
SKILL_CODES = {"Clarity": "cl", "Empathy": "em", "Assertiveness": "as", "Composure": "co", "Grammar & word choice": "gr"}
CARE_MESSAGE = (
    "I'm stepping out of the role-play for a moment. It sounds like you might be going through something hard, "
    "and that matters more than practice. In India you can call **Tele-MANAS on 14416** (free, 24/7) to talk to a "
    "counsellor, or reach out to someone you trust. If you're in immediate danger, call **112**. "
    "Whenever you're ready, you can continue or end the session."
)

# ------------------------------------------------------------------ styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Nunito:wght@400;600;700&display=swap');
:root { --clay:#C8553D; --ink:#2B2118; --soft:#7A6A5D; --cream:#FFF8F1; --sand:#F3E6D8; }
html, body, [class*="css"], .stMarkdown, .stButton button, textarea { font-family:'Nunito', system-ui, sans-serif; }
h1, h2, h3, .sir-title { font-family:'Fraunces', Georgia, serif !important; color: var(--ink); }
.sir-title { font-size: clamp(2.2rem, 6vw, 3.2rem); line-height:1.05; margin: .3rem 0 .4rem; }
.sir-sub { color: var(--soft); font-size: 1.08rem; line-height: 1.55; }
.card { background:#fff; border:1px solid #EADBC9; border-radius:16px; padding:14px 16px; margin-bottom:8px; min-height:132px; }
.card .em { font-size:1.6rem; } .card .t { font-weight:700; color:var(--ink); margin:4px 0 2px; line-height:1.25; }
.card .w { color:var(--soft); font-size:.9rem; }
.head { display:flex; align-items:center; gap:12px; background:#fff; border:1px solid #EADBC9; border-radius:16px; padding:10px 14px; }
.head .av { font-size:2rem; } .head .n { font-weight:700; color:var(--ink); } .head .r { color:var(--soft); font-size:.88rem; }
.goal { background: var(--sand); border-radius: 999px; padding: 4px 12px; font-size:.88rem; color: var(--ink); display:inline-block; margin:8px 0 4px; }
.meter { margin: 10px 0 4px; }
.meter .lbl { display:flex; justify-content:space-between; font-size:.9rem; color:var(--ink); font-weight:600; }
.meter .track { position:relative; height:12px; border-radius:999px; background: linear-gradient(90deg,#E07A5F,#F2CC8F,#81B29A); }
.meter .dot { position:absolute; top:-5px; width:22px; height:22px; border-radius:50%; background:#fff; border:3px solid var(--ink); transform:translateX(-50%); transition:left .4s; }
.chat { display:flex; flex-direction:column; gap:10px; margin-top:12px; }
.b { max-width: 82%; padding:10px 14px; border-radius:18px; line-height:1.45; font-size:1rem; }
.them { align-self:flex-start; background:#fff; border:1px solid #EADBC9; border-bottom-left-radius:6px; }
.you { align-self:flex-end; background: var(--clay); color:#fff; border-bottom-right-radius:6px; }
.tip { align-self:flex-end; max-width:82%; font-size:.86rem; color: var(--soft); text-align:right; margin-top:-4px; }
.chip { display:inline-block; background: var(--sand); color: var(--ink); border-radius:999px; padding:1px 9px; font-size:.78rem; font-weight:700; margin-right:4px; }
.note { align-self:center; max-width:92%; background:#FFF1E6; border:1px dashed #E3B58F; border-radius:12px; padding:8px 12px; font-size:.92rem; color:var(--ink); }
.big { font-family:'Fraunces', Georgia, serif; font-size:4rem; color: var(--clay); line-height:1; }
.skill { margin: 6px 0; } .skill .row { display:flex; justify-content:space-between; font-size:.95rem; }
.skill .bar { height:8px; background: var(--sand); border-radius:999px; overflow:hidden; } .skill .bar > div { height:100%; background: var(--clay); }
.rw { background:#fff; border:1px solid #EADBC9; border-radius:12px; padding:10px 12px; margin:8px 0; }
.rw .x { color:#9A5B4C; text-decoration: line-through; } .rw .y { color:#2F6B4F; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ state
DEFAULTS = dict(phase="home", scenario=None, messages=[], openness=50, turns=0, coach_live=True,
                outcome="", debrief=None, notice=None, pending=None)
S = st.session_state
for k, v in DEFAULTS.items():
    if k not in S:
        S[k] = v.copy() if isinstance(v, (list, dict)) else v
if "sessions" not in S:
    S.sessions = progress.decode(st.query_params.get("s", ""))


def _secret(name):
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.environ.get(name)


def api_key():
    key = _secret("GROQ_API_KEY") or _secret("GEMINI_API_KEY")
    return str(key).strip().strip('"').strip("'") if key else None


def provider():
    return PROVIDER_NAMES[detect_provider(api_key())] if api_key() else "an AI service"


def client():
    key = api_key()
    if not key:
        raise LLMError("The app isn't connected to an AI service yet. The owner needs to add GROQ_API_KEY in Streamlit Secrets.")
    if S.get("_ck") != key:
        S["_c"], S["_ck"] = LLMClient(key, _secret("LLM_MODEL")), key
    return S["_c"]


# ------------------------------------------------------------------ conversation logic
def add(role, text, **extra):
    S.messages.append({"role": role, "text": text, **extra})


def start(scenario):
    S.scenario, S.messages, S.turns, S.outcome, S.debrief = scenario, [], 0, "", None
    S.openness = scenario["start"]
    S.phase = "talk"
    if scenario["opening"]:
        add("them", scenario["opening"])
        return
    try:
        data = client().generate_json(roleplay_system(scenario), opening_prompt(), temperature=0.8)
        add("them", str(data.get("reply") or "Hi. What did you want to talk about?"))
    except (LLMError, BadOutput) as e:
        add("them", "Hi. What did you want to talk about?")
        if isinstance(e, LLMError):
            S.notice = e.user_message


def respond(user_text, shown_text=None):
    add("user", shown_text or user_text)
    try:
        data = client().generate_json(roleplay_system(S.scenario), turn_prompt(S.messages[:-1], user_text, S.openness), 0.7)
    except LLMError as e:
        S.messages.pop()
        S.notice = e.user_message
        return
    except BadOutput:
        add("note", "The other side went quiet for a second. Could you say that again?")
        return

    intent = data.get("intent", "in_scenario")
    me = S.messages[-1]
    if intent == "distress":
        add("note", CARE_MESSAGE, care=True)
        return
    if intent in ("off_topic", "injection"):
        add("note", f"Let's stay in the conversation with {S.scenario['who']}. What would you say to them next?")
        return
    if intent == "stuck":
        add("note", f"💭 Try something like: *\"{data.get('stronger_line') or 'Can I explain why this matters to me?'}\"*")
        return

    S.turns += 1
    change = max(-2, min(2, int(data.get("openness_change") or 0)))
    S.openness = max(0, min(100, S.openness + change * OPENNESS_STEP))
    me.update(tone=data.get("tone", ""), tip=data.get("coach_tip", ""), change=change,
              fix=data.get("grammar_fix") if isinstance(data.get("grammar_fix"), dict) else None,
              stronger=data.get("stronger_line", ""))
    reply = str(data.get("reply") or "").strip()
    if reply:
        add("them", reply)
    if data.get("goal_reached") and S.openness >= 60:
        S.outcome = "Goal reached"
        finish()
    elif S.turns >= MAX_TURNS:
        S.outcome = "Ran out of turns"
        finish()


def finish():
    S.outcome = S.outcome or "Ended early"
    S.phase = "debrief"
    user_msgs = [m for m in S.messages if m["role"] == "user"]
    if not user_msgs:
        S.debrief = None
        return
    try:
        d = client().generate_json(DEBRIEF_SYSTEM, debrief_prompt(S.scenario, S.messages, S.outcome), 0.3)
        scores = {k: max(1, min(5, int(d.get("scores", {}).get(k, 3)))) for k in SKILLS}
    except (LLMError, BadOutput, ValueError, TypeError):
        d, scores = {}, None
    if scores is None:  # fallback: estimate from openness so the session still counts
        base = 1 + round(S.openness / 25)
        scores, d = {k: base for k in SKILLS}, {"headline": "Debrief unavailable right now; here's an estimate from the conversation."}
    overall = round(mean(scores.values()) * 20)
    S.debrief = {**d, "scores": scores, "overall": overall}
    S.sessions.append({"d": datetime.now().strftime("%d %b"), "sc": S.scenario["id"], "score": overall,
                       "open": S.openness, "ok": S.outcome == "Goal reached",
                       "sk": {SKILL_CODES[k]: v for k, v in scores.items()}})
    st.query_params["s"] = progress.encode(S.sessions)


# ------------------------------------------------------------------ rendering
def face(o):
    return "😟" if o < 30 else "😐" if o < 55 else "🙂" if o < 80 else "😊"


def meter():
    s = S.scenario
    st.markdown(f"""<div class="meter"><div class="lbl"><span>{html.escape(s['who'])}'s openness</span>
        <span>{face(S.openness)} {S.openness}%</span></div>
        <div class="track"><div class="dot" style="left:{S.openness}%"></div></div></div>""", unsafe_allow_html=True)


def chat_html():
    out = ['<div class="chat">']
    for m in S.messages:
        text = html.escape(m["text"]).replace("\n", "<br>")
        if m["role"] == "them":
            out.append(f'<div class="b them">{text}</div>')
        elif m["role"] == "user":
            out.append(f'<div class="b you">{text}</div>')
            if S.coach_live and m.get("tip"):
                arrow = "▲" if m.get("change", 0) > 0 else "▼" if m.get("change", 0) < 0 else "▬"
                fix = m.get("fix")
                fix_html = (f'<br>✏️ <s>{html.escape(str(fix.get("original", "")))}</s> → '
                            f'<b>{html.escape(str(fix.get("better", "")))}</b>') if fix and fix.get("better") else ""
                out.append(f'<div class="tip"><span class="chip">{html.escape(m.get("tone", ""))}</span>'
                           f'<span class="chip">{arrow} openness</span> {html.escape(m["tip"])}{fix_html}</div>')
        else:
            body = html.escape(m["text"].replace("*", ""))
            out.append(f'<div class="note">{body}</div>')
    out.append("</div>")
    return "".join(out)


def progress_block():
    if not S.sessions:
        return
    st.markdown("#### Your progress")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sessions", len(S.sessions))
    c2.metric("Latest score", f"{S.sessions[-1]['score']}/100",
              f"{S.sessions[-1]['score'] - S.sessions[-2]['score']:+d}" if len(S.sessions) > 1 else None)
    c3.metric("Goals reached", sum(1 for s in S.sessions if s.get("ok")))
    if len(S.sessions) >= 2:
        st.line_chart({"Score": [s["score"] for s in S.sessions]}, height=160, color="#C8553D")


# ------------------------------------------------------------------ pages
if S.notice:
    st.error(S.notice)
    S.notice = None

if S.phase == "home":
    st.markdown('<div class="sir-title">Say It Right</div>', unsafe_allow_html=True)
    st.markdown('<div class="sir-sub">Rehearse the conversation you keep putting off. An AI plays the other person, '
                'a private coach helps with your tone and words, and you walk in ready.</div>', unsafe_allow_html=True)
    st.write("")
    progress_block()
    st.markdown("#### Pick a conversation")
    cols = st.columns(2)
    for i, s in enumerate(SCENARIOS):
        with cols[i % 2]:
            st.markdown(f'<div class="card"><div class="em">{s["emoji"]}</div><div class="t">{html.escape(s["title"])}</div>'
                        f'<div class="w">With {html.escape(s["who"])}, {html.escape(s["role"].lower())}</div></div>',
                        unsafe_allow_html=True)
            if st.button("Start", key=f"go_{s['id']}", width="stretch", disabled=not api_key()):
                start(s)
                st.rerun()
    with st.expander("✨ Or describe your own conversation"):
        who = st.text_input("Who are you talking to?", placeholder="e.g. My landlord, Mr. Sharma")
        situation = st.text_area("What's the situation?", placeholder="e.g. He wants to keep my full deposit for normal wear and tear.", height=90)
        goal = st.text_input("What do you want to achieve?", placeholder="e.g. Get at least 80% of the deposit back")
        ok = len(who.strip()) >= 2 and len(situation.strip()) >= 20 and len(goal.strip()) >= 5
        if st.button("Start my conversation", disabled=not (ok and api_key())):
            start(custom_scenario(who, situation, goal))
            st.rerun()
        if not ok:
            st.caption("Fill in all three (the situation needs at least 20 characters).")
    S.coach_live = st.toggle("Show coach tips during the conversation", value=S.coach_live,
                             help="Turn off for a more realistic rehearsal; you'll still get the full debrief.")
    if not api_key():
        st.warning("The app isn't connected to an AI service yet. The owner needs to add GROQ_API_KEY in Streamlit Secrets.")
    st.caption(f"Say It Right is an AI practice tool powered by {provider()}. The people you talk to are AI role-play "
               f"characters, not real people. Your messages are sent to {provider()}'s API; nothing is stored on a server, "
               "and your progress lives only in this page's link. It is not therapy or professional advice.")

elif S.phase == "talk":
    s = S.scenario
    typed = st.chat_input(f"Say something to {s['who']}...")
    action, S.pending = S.pending, None
    if action == "stuck":
        with st.spinner("Thinking of an opener..."):
            respond("I don't know what to say next. Help me.", shown_text="💭 I'm stuck")
    elif action == "end":
        with st.spinner("Writing your debrief..."):
            finish()
        st.rerun()
    if typed is not None:
        t = typed.strip()
        if not t:
            st.toast("Type what you'd say first.")
        elif len(t) > MAX_CHARS:
            st.toast(f"Keep it under {MAX_CHARS} characters. Real conversations happen in short turns.")
        else:
            with st.spinner(f"{s['who']} is replying..."):
                respond(t)
        st.rerun()

    st.markdown(f'<div class="head"><div class="av">{s["emoji"]}</div><div><div class="n">{html.escape(s["who"])} '
                f'<span style="font-weight:400;color:#7A6A5D">· AI role-play</span></div>'
                f'<div class="r">{html.escape(s["role"])}</div></div></div>', unsafe_allow_html=True)
    st.markdown(f'<span class="goal">🎯 {html.escape(s["goal"])}</span>', unsafe_allow_html=True)
    meter()
    st.markdown(chat_html(), unsafe_allow_html=True)
    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.button("💭 I'm stuck", on_click=lambda: S.update(pending="stuck"), width="stretch")
    c2.button("End & debrief", on_click=lambda: S.update(pending="end"), width="stretch", type="primary",
              disabled=not any(m["role"] == "user" for m in S.messages))
    if c3.button("Leave", width="stretch"):
        S.phase = "home"
        st.rerun()
    st.caption(f"Turn {S.turns} of {MAX_TURNS} · {s['who']} is an AI character.")

elif S.phase == "debrief":
    s, d = S.scenario, S.debrief
    st.markdown(f"### {s['emoji']} {html.escape(s['title'])}")
    if not d:
        st.write("You didn't say anything this time, so there's nothing to review. Give it another go!")
    else:
        c1, c2 = st.columns([1, 2])
        c1.markdown(f'<div class="big">{d["overall"]}</div><div style="color:#7A6A5D">out of 100</div>', unsafe_allow_html=True)
        c2.markdown(f"**{'🎉 Goal reached' if S.outcome == 'Goal reached' else '⏳ ' + S.outcome}** · "
                    f"{s['who']} ended at {face(S.openness)} {S.openness}% openness")
        if d.get("headline"):
            c2.markdown(f"*{d['headline']}*")
        st.markdown("#### Your skills")
        for k in SKILLS:
            v = d["scores"][k]
            st.markdown(f'<div class="skill"><div class="row"><span>{k}</span><span>{v}/5</span></div>'
                        f'<div class="bar"><div style="width:{v * 20}%"></div></div></div>', unsafe_allow_html=True)
        if d.get("did_well") or d.get("practise"):
            st.markdown("#### Coach's notes")
            if d.get("did_well"):
                st.markdown(f"🌱 **You did well:** {d['did_well']}")
            if d.get("practise"):
                st.markdown(f"🎯 **Practise next:** {d['practise']}")
        if d.get("rewrites"):
            st.markdown("#### Say it better")
            for r in d["rewrites"][:3]:
                st.markdown(f'<div class="rw"><div class="x">{html.escape(str(r.get("you_said", "")))}</div>'
                            f'<div class="y">→ {html.escape(str(r.get("try", "")))}</div></div>', unsafe_allow_html=True)
        st.caption("Progress saved to this page's link. Bookmark it to keep your history.")
    progress_block()
    c1, c2 = st.columns(2)
    if c1.button("Try this conversation again", type="primary", width="stretch"):
        start(BY_ID.get(s["id"], s))
        st.rerun()
    if c2.button("Pick another conversation", width="stretch"):
        S.phase = "home"
        st.rerun()
    st.download_button("Download my progress", json.dumps(S.sessions, indent=1), "say_it_right_progress.json")
