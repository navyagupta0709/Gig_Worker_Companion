import json
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

st.set_page_config(page_title="Saathi | Gig Worker Companion", page_icon="🤝", layout="centered")

# ---------------- Styling ----------------
CSS = "".join([
    "<style>",
    "#MainMenu, footer {visibility: hidden;}",
    ".stApp {background: linear-gradient(180deg,#f3f0ff 0%,#fff5f8 50%,#eefcf7 100%);}",
    ".block-container {padding-top: 1.2rem; max-width: 820px;}",
    ".hero {background: linear-gradient(135deg,#6a11cb 0%,#2575fc 50%,#00c9a7 100%);",
    "border-radius: 22px; padding: 28px 30px; color: #fff; margin-bottom: 18px;",
    "box-shadow: 0 12px 30px rgba(106,17,203,.30);}",
    ".hero h1 {margin: 0; font-size: 2.3rem; color: #fff;}",
    ".hero p {margin: 6px 0 14px 0; font-size: 1.05rem; color: #fff; opacity: .95;}",
    ".chip {display: inline-block; background: rgba(255,255,255,.22); border-radius: 999px;",
    "padding: 4px 12px; margin: 0 6px 6px 0; font-size: .82rem; font-weight: 600; color: #fff;}",
    ".fcard {border-radius: 16px; padding: 16px 10px; text-align: center; color: #fff;",
    "box-shadow: 0 6px 16px rgba(0,0,0,.12); height: 100%;}",
    ".fcard .ic {font-size: 1.9rem;}",
    ".fcard b {display: block; margin: 6px 0 2px 0; color: #fff;}",
    ".fcard span {font-size: .8rem; color: #fff; opacity: .92;}",
    ".c1 {background: linear-gradient(135deg,#ff9a44,#fc6076);}",
    ".c2 {background: linear-gradient(135deg,#43e97b,#11998e);}",
    ".c3 {background: linear-gradient(135deg,#667eea,#764ba2);}",
    "[data-testid='stMetric'] {background: #fff; border-radius: 14px; padding: 14px 16px;",
    "border-left: 6px solid #6a11cb; box-shadow: 0 4px 14px rgba(0,0,0,.08);}",
    ".stTabs [data-baseweb='tab-list'] {gap: 6px;}",
    ".stTabs [data-baseweb='tab'] {background: #ffffff; border-radius: 12px; padding: 8px 14px;",
    "box-shadow: 0 2px 8px rgba(0,0,0,.06);}",
    ".stTabs [aria-selected='true'] {background: linear-gradient(135deg,#6a11cb,#2575fc) !important;",
    "color: #fff !important;}",
    ".stButton > button {border-radius: 12px; font-weight: 700; border: none; color: #fff;",
    "background: linear-gradient(135deg,#ff6a88,#ff9a44);}",
    ".stButton > button:hover {filter: brightness(1.08); color: #fff;}",
    ".sec-title {font-size: 1.2rem; font-weight: 800; color: #4a1d96; margin: 4px 0 8px 0;}",
    ".disclaimer {text-align: center; color: #6b7280; font-size: .8rem; margin-top: 10px;}",
    "</style>",
])
st.markdown(CSS, unsafe_allow_html=True)

# ---------------- Gemini setup ----------------
try:
    API_KEY = str(st.secrets["GEMINI_API_KEY"]).strip()
except Exception:
    st.error("Secrets mein GEMINI_API_KEY add karo (Manage app → Settings → Secrets).")
    st.stop()

client = genai.Client(api_key=API_KEY)
MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]

# ---------------- Sidebar ----------------
st.sidebar.markdown("### 🤝 Saathi")
lang = st.sidebar.selectbox(
    "🌐 Bhasha / Language",
    ["Hinglish", "Hindi", "English", "Marathi", "Tamil", "Telugu", "Bengali", "Kannada"],
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Kya kar sakta hoon?**\n\n"
    "- 💬 Safety aur haq ki jaankari\n"
    "- 💰 Kamai ka hisaab\n"
    "- 🏛 Sarkari yojana\n"
    "- 📄 Document samjhana\n"
    "- ✍️ Shikayat likhna"
)
st.sidebar.caption("Powered by Google Gemini")

SYSTEM = (
    f"You are Saathi, a friendly assistant for gig and informal workers in India. "
    f"Reply in {lang}, very simple words, short sentences. Help with earnings, safety, "
    "rights and welfare schemes (e-Shram, Ayushman Bharat, PM-SYM, PM-SVANidhi), "
    "documents and grievance drafting. Never guarantee eligibility or legal outcomes; "
    "suggest official sources or helplines. Keep answers under 150 words."
)


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

# ---------------- Hero ----------------
HERO = (
    "<div class='hero'>"
    "<h1>🤝 Saathi</h1>"
    "<p>Delivery partners, drivers aur daily-wage workers ka apna AI saathi</p>"
    "<span class='chip'>🌐 8 Languages</span>"
    "<span class='chip'>✨ Powered by Gemini</span>"
    "<span class='chip'>🛠 5 Smart Tools</span>"
    "<span class='chip'>🗣 Simple Language</span>"
    "</div>"
)
st.markdown(HERO, unsafe_allow_html=True)

t1, t2, t3, t4, t5 = st.tabs(["💬 Chat", "💰 Kamai", "🏛 Yojana", "📄 Document", "✍️ Shikayat"])

# ---------------- Chat ----------------
with t1:
    if not st.session_state.msgs:
        k1, k2, k3 = st.columns(3)
        k1.markdown("<div class='fcard c1'><div class='ic'>🛵</div><b>Safety</b><span>Raat, barish aur accident ke tips</span></div>", unsafe_allow_html=True)
        k2.markdown("<div class='fcard c2'><div class='ic'>⚖️</div><b>Haq</b><span>Apne rights aur welfare schemes</span></div>", unsafe_allow_html=True)
        k3.markdown("<div class='fcard c3'><div class='ic'>🗣</div><b>Apni bhasha</b><span>Hindi, English aur regional</span></div>", unsafe_allow_html=True)
        st.write("")

    quick = None
    b1, b2, b3 = st.columns(3)
    if b1.button("🛵 Raat ki safety", use_container_width=True):
        quick = "Raat ko delivery karte time safety ke liye kya dhyan rakhun?"
    if b2.button("⚖️ Mere haq", use_container_width=True):
        quick = "Ek gig worker ke kaun se haq hote hain?"
    if b3.button("🏥 Health scheme", use_container_width=True):
        quick = "Gig worker ke liye health insurance ki kaun si scheme hai?"

    for m in st.session_state.msgs:
        with st.chat_message(m["role"], avatar="🧑" if m["role"] == "user" else "🤝"):
            st.write(m["content"])

    q = st.chat_input("Kuch bhi poochho: safety, schemes, haq...") or quick
    if q:
        st.session_state.msgs.append({"role": "user", "content": q})
        with st.chat_message("user", avatar="🧑"):
            st.write(q)
        hist = "\n".join(f"{m['role']}: {m['content']}" for m in st.session_state.msgs[-6:])
        with st.chat_message("assistant", avatar="🤝"):
            with st.spinner("Saathi soch raha hai..."):
                a = ask(hist)
            st.write(a)
        st.session_state.msgs.append({"role": "assistant", "content": a})

# ---------------- Earnings ----------------
with t2:
    st.markdown("<div class='sec-title'>💰 Aaj ki kamai</div>", unsafe_allow_html=True)
    txt = st.text_input("Apni kamai likho", placeholder="Aaj Swiggy se 850 kamaye, petrol 200")
    st.caption("Payment kam aaya? Likho: 'Uber ne 600 ki jagah 450 diye, petrol 150'")
    if st.button("Save karo") and txt.strip():
        try:
            EX = (
                "Extract from this gig worker message. Return JSON only with keys: "
                "platform (string), amount (number), expense (number, 0 if none), "
                "expected_amount (number or null, only if they got less than promised), "
                "note (string). Message: " + txt
            )
            r = gen(EX, types.GenerateContentConfig(response_mime_type="application/json"))
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
        a.metric("Total kamai", f"₹{df.amount.sum():.0f}")
        b.metric("Kharcha", f"₹{df.expense.sum():.0f}")
        c.metric("Bachat", f"₹{df.net.sum():.0f}")
        st.bar_chart(df.groupby("platform")["net"].sum(), color="#6a11cb")
        if st.button("📊 Summary + tips"):
            with st.spinner("Summary ban rahi hai..."):
                st.write(ask("Is earnings ka simple summary aur 2 bachat tips do:\n" + df.to_string(index=False)))
    else:
        st.info("Abhi koi kamai save nahi hui. Upar likh ke shuru karo 👆")

# ---------------- Schemes ----------------
with t3:
    st.markdown("<div class='sec-title'>🏛 Kaun si yojana mere liye hai?</div>", unsafe_allow_html=True)
    with st.form("f"):
        s1, s2 = st.columns(2)
        age = s1.number_input("Umar", 14, 80, 28)
        state = s2.text_input("Rajya", placeholder="Punjab")
        work = st.selectbox("Kaam ka type", ["Delivery partner", "Cab / auto driver", "Daily-wage", "Street vendor", "Domestic worker", "Other"])
        go = st.form_submit_button("🔍 Yojana dhundo")
    if go:
        with st.spinner("Yojana dhundh raha hoon..."):
            st.write(ask(f"Worker: age {age}, state {state or 'not given'}, work {work}. Suggest up to 4 relevant "
                         "Indian govt schemes with one-line benefit and next step. Say eligibility must be "
                         "confirmed on the official portal."))

# ---------------- Documents ----------------
with t4:
    st.markdown("<div class='sec-title'>📄 Document samjho</div>", unsafe_allow_html=True)
    up = st.file_uploader("ID, notice ya payment screenshot ki photo", type=["png", "jpg", "jpeg"])
    if up:
        st.image(up, width=300)
        if st.button("🔎 Samjhao"):
            with st.spinner("Document padh raha hoon..."):
                st.write(ask("Is document mein kya likha hai, simple bhasha mein samjhao. Deadline, amount "
                             "aur next step batao.", image=up))
    st.caption("🔒 Privacy: Aadhaar, bank details aur OTP hide karke upload karo.")

# ---------------- Grievance ----------------
with t5:
    st.markdown("<div class='sec-title'>✍️ Shikayat draft karo</div>", unsafe_allow_html=True)
    issue = st.text_area("Kya hua? (kab, kitna paisa, kisne)", value=st.session_state.issue, height=120)
    to = st.selectbox("Kisko bhejni hai?", ["Company support", "Labour department", "Consumer helpline (1915)"])
    if st.button("📝 Shikayat likho") and issue.strip():
        with st.spinner("Shikayat taiyar ho rahi hai..."):
            st.session_state.draft = ask(f"Write a short polite complaint for {to}. Use only the facts given, "
                                         f"invent nothing. Include subject, issue, requested action. Details: {issue}")
    if st.session_state.draft:
        st.text_area("Copy karo", st.session_state.draft, height=300)
        st.caption("Bhejne se pehle details check kar lo.")

DISC = (
    "<div class='disclaimer'>Saathi general jaankari deta hai, legal advice nahi. "
    "Scheme eligibility aur complaint process official source se verify karein.</div>"
)
st.markdown(DISC, unsafe_allow_html=True)
