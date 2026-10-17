import json
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

st.set_page_config(page_title="Saathi", page_icon="🤝")


CSS = "".join([
    "<style>",
    "#MainMenu, footer {visibility: hidden;}",
    ".stApp {background: linear-gradient(180deg,#f3f0ff 0%,#fff5f8 50%,#eefcf7 100%);}",
    ".block-container {padding-top: 1.2rem; max-width: 820px;}",
    ".hero {background: linear-gradient(135deg,#6a11cb 0%,#2575fc 50%,#00c9a7 100%);",
    "border-radius: 22px; padding: 26px 28px; color: #fff; margin-bottom: 16px;",
    "box-shadow: 0 12px 30px rgba(106,17,203,.30);}",
    ".hero h1 {margin: 0; font-size: 2.2rem; color: #fff;}",
    ".hero p {margin: 6px 0 12px 0; font-size: 1.02rem; color: #fff; opacity: .95;}",
    ".chip {display: inline-block; background: rgba(255,255,255,.22); border-radius: 999px;",
    "padding: 4px 12px; margin: 0 6px 6px 0; font-size: .82rem; font-weight: 600; color: #fff;}",
    "[data-testid='stMetric'] {background: #fff; border-radius: 14px; padding: 14px 16px;",
    "border-left: 6px solid #6a11cb; box-shadow: 0 4px 14px rgba(0,0,0,.08);}",
    ".stTabs [data-baseweb='tab-list'] {gap: 6px;}",
    ".stTabs [data-baseweb='tab'] {background: #ffffff; border-radius: 12px; padding: 8px 14px;",
    "box-shadow: 0 2px 8px rgba(0,0,0,.06);}",
    ".stTabs [aria-selected='true'] {background: linear-gradient(135deg,#6a11cb,#2575fc) !important;",
    "color: #fff !important;}",
    ".stButton > button, .stFormSubmitButton > button {border-radius: 12px; font-weight: 700;",
    "border: none; color: #fff; background: linear-gradient(135deg,#ff6a88,#ff9a44);}",
    ".stButton > button:hover, .stFormSubmitButton > button:hover {filter: brightness(1.08); color: #fff;}",
    "[data-testid='stSidebar'] {background: linear-gradient(180deg,#ede7ff,#e3f6ff);}",
    "</style>",
])
st.markdown(CSS, unsafe_allow_html=True)

HERO = (
    "<div class='hero'>"
    "<h1>🤝 Saathi</h1>"
    "<p>Gig workers ka apna saathi: kamai, suraksha, haq aur shikayat</p>"
    "<span class='chip'>🌐 8 Languages</span>"
    "<span class='chip'>✨ Powered by Gemini</span>"
    "<span class='chip'>🛠 5 Smart Tools</span>"
    "</div>"
)
st.markdown(HERO, unsafe_allow_html=True)

try:
    API_KEY = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    st.error("Secrets mein GEMINI_API_KEY add karo (Manage app → Settings → Secrets).")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]

lang = st.sidebar.selectbox("🌐 Bhasha", ["Hinglish", "Hindi", "English", "Marathi", "Tamil", "Telugu", "Bengali", "Kannada"])

SYSTEM = f"""You are Saathi, a friendly assistant for gig and informal workers in India.
Reply in {lang}, very simple words, short sentences. Help with earnings, safety,
rights and welfare schemes (e-Shram, Ayushman Bharat, PM-SYM, PM-SVANidhi),
documents and grievance drafting. Never guarantee eligibility or legal outcomes;
suggest official sources or helplines. Keep answers under 150 words."""


def gen(contents, config):
    err = None
    for m in MODELS:
        try:
            return client.models.generate_content(model=m, contents=contents, config=config)
        except Exception as e:
            err = e
    raise err


def ask(prompt, image=None):
    parts = [types.Part(text=prompt)]
    if image is not None:
        parts.append(types.Part.from_bytes(data=image.getvalue(), mime_type=image.type or "image/jpeg"))
    try:
        r = gen([types.Content(role="user", parts=parts)],
                types.GenerateContentConfig(system_instruction=SYSTEM))
        return r.text or "Dobara try karo."
    except Exception as e:
        st.sidebar.error(f"Gemini error: {e}")
        return "Abhi service available nahi hai. Thodi der baad try karo."


st.session_state.setdefault("msgs", [])
st.session_state.setdefault("earn", [])
st.session_state.setdefault("issue", "")
st.session_state.setdefault("draft", "")

t1, t2, t3, t4, t5 = st.tabs(["💬 Chat", "💰 Kamai", "🏛 Yojana", "📄 Document", "✍️ Shikayat"])

with t1:
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    q = st.chat_input("Kuch bhi poochho: safety, schemes, haq...")
    if q:
        st.session_state.msgs.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.write(q)
        hist = "\n".join(f"{m['role']}: {m['content']}" for m in st.session_state.msgs[-6:])
        with st.chat_message("assistant"):
            with st.spinner("Soch raha hoon..."):
                a = ask(hist)
            st.write(a)
        st.session_state.msgs.append({"role": "assistant", "content": a})

with t2:
    txt = st.text_input("Aaj ki kamai likho", placeholder="Aaj Swiggy se 850 kamaye, petrol 200")
    st.caption("Payment kam aaya? Likho: 'Uber ne 600 ki jagah 450 diye, petrol 150'")
    if st.button("Save karo") and txt.strip():
        try:
            r = gen(
                f"""Extract from this gig worker message. Return JSON only with keys:
platform (string), amount (number), expense (number, 0 if none),
expected_amount (number or null, only if they got less than promised), note (string).
Message: {txt}""",
                types.GenerateContentConfig(response_mime_type="application/json"))
            d = json.loads(r.text)
            amt = float(d["amount"])
            exp_cost = float(d.get("expense") or 0)
            plat = str(d.get("platform") or "Other")
            st.session_state.earn.append({"platform": plat, "amount": amt, "expense": exp_cost})
            st.success(f"✅ {plat}: ₹{amt:.0f} kamai, ₹{exp_cost:.0f} kharcha")
            ea = d.get("expected_amount")
            if ea and float(ea) > amt:
                st.warning(f"⚠️ ₹{float(ea) - amt:.0f} kam mile.")
                st.session_state.issue = f"{plat} ne mujhe ₹{float(ea):.0f} ki jagah sirf ₹{amt:.0f} diye."
                st.info("👉 Shikayat tab kholo, details bhari hui hain.")
        except Exception:
            st.error("Samajh nahi aaya. Platform aur amount clearly likho.")
    if st.session_state.earn:
        df = pd.DataFrame(st.session_state.earn)
        df["net"] = df["amount"] - df["expense"]
        a, b, c = st.columns(3)
        a.metric("Kamai", f"₹{df.amount.sum():.0f}")
        b.metric("Kharcha", f"₹{df.expense.sum():.0f}")
        c.metric("Bachat", f"₹{df.net.sum():.0f}")
        st.bar_chart(df.set_index("platform")["net"])
        if st.button("📊 Summary + tips"):
            st.write(ask("Is earnings ka simple summary aur 2 bachat tips do:\n" + df.to_string(index=False)))

with t3:
    with st.form("f"):
        age = st.number_input("Umar", 14, 80, 28)
        state = st.text_input("Rajya", placeholder="Punjab")
        work = st.selectbox("Kaam", ["Delivery partner", "Cab / auto driver", "Daily-wage", "Street vendor", "Domestic worker", "Other"])
        go = st.form_submit_button("Yojana dhundo")
    if go:
        with st.spinner("Dhundh raha hoon..."):
            st.write(ask(f"Worker: age {age}, state {state or 'not given'}, work {work}. Suggest up to 4 relevant "
                         "Indian govt schemes with one-line benefit and next step. Say eligibility must be "
                         "confirmed on the official portal."))

with t4:
    up = st.file_uploader("ID, notice ya payment screenshot", type=["png", "jpg", "jpeg"])
    if up:
        st.image(up, width=300)
        if st.button("Samjhao"):
            with st.spinner("Padh raha hoon..."):
                st.write(ask("Is document mein kya likha hai, simple bhasha mein samjhao. Deadline, amount "
                             "aur next step batao.", image=up))
    st.caption("Privacy: Aadhaar, bank details aur OTP hide karke upload karo.")

with t5:
    issue = st.text_area("Kya hua? (kab, kitna paisa, kisne)", value=st.session_state.issue, height=120)
    to = st.selectbox("Kisko bhejni hai?", ["Company support", "Labour department", "Consumer helpline (1915)"])
    if st.button("Shikayat likho") and issue.strip():
        with st.spinner("Likh raha hoon..."):
            st.session_state.draft = ask(f"Write a short polite complaint for {to}. Use only the facts given, "
                                         f"invent nothing. Include subject, issue, requested action. Details: {issue}")
    if st.session_state.draft:
        st.text_area("Copy karo", st.session_state.draft, height=300)

st.divider()
st.caption("Saathi general jaankari deta hai, legal advice nahi. Official source se verify karein.")
