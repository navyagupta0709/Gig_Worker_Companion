import os
import json
import uuid
import sqlite3
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------------
# Saathi: Gig Worker Companion (PromptWars Warm-up Challenge)
# ---------------------------------------------------------------

st.set_page_config(
    page_title="Saathi | Gig Worker Companion",
    page_icon="🤝",
    layout="centered",
)

MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]  # fallback order


# ---------- Gemini client ----------
def get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.environ.get("GEMINI_API_KEY")


@st.cache_resource
def get_client(api_key: str):
    # Keys starting with "AQ." come from Google Cloud (Vertex AI express mode)
    if api_key.startswith("AQ."):
        return genai.Client(vertexai=True, api_key=api_key)
    return genai.Client(api_key=api_key)


API_KEY = get_api_key()
if not API_KEY:
    st.error(
        "Gemini API key nahi mili. Streamlit Cloud mein "
        "App settings → Secrets mein GEMINI_API_KEY set karo."
    )
    st.stop()

client = get_client(API_KEY)


def generate(contents, config=None):
    """Call Gemini, trying fallback models if one fails."""
    last_error = None
    for model in MODELS:
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise last_error


# ---------- Database (per-user rows) ----------
db = sqlite3.connect(Path("saathi.db"), check_same_thread=False)
db.execute(
    """
    CREATE TABLE IF NOT EXISTS earnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        day TEXT NOT NULL,
        platform TEXT NOT NULL,
        amount REAL NOT NULL,
        expense REAL NOT NULL DEFAULT 0,
        note TEXT DEFAULT ''
    )
    """
)
db.commit()

st.session_state.setdefault("uid", uuid.uuid4().hex)
UID = st.session_state["uid"]

# ---------- Sidebar ----------
LANGS = ["Hinglish", "Hindi", "English", "Marathi",
         "Tamil", "Telugu", "Bengali", "Kannada"]
lang = st.sidebar.selectbox("🌐 Bhasha / Language", LANGS)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Saathi gig workers ke liye banaya gaya GenAI assistant hai: "
    "kamai, suraksha, haq, yojana, document aur shikayat."
)
debug_box = st.sidebar.expander("🛠 Debug")


def system_prompt():
    return f"""
You are Saathi, a friendly assistant for gig and informal workers in India
(delivery partners, drivers, and daily-wage workers).
- Reply in {lang}, using very simple words and short sentences.
- Help with earnings, safety practices, rights and welfare schemes
  (e-Shram, Ayushman Bharat, PM-SVANidhi, PM-SYM, and applicable labour rules),
  document explanation, and grievance drafting.
- For scheme eligibility, ask up to 2-3 short questions (age, state, type of
  work) before suggesting options.
- Do not guarantee eligibility or legal outcomes.
- For uncertain or urgent matters, recommend checking the official government
  source or a helpline / legal-aid service.
- Keep answers under 150 words unless the user asks for more.
"""


def ask(prompt, history=None, image=None):
    contents = []
    for m in history or []:
        role = "user" if m.get("role") == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=str(m.get("content", "")))])
        )

    parts = [types.Part(text=prompt)]
    if image is not None:
        parts.append(
            types.Part.from_bytes(
                data=image.getvalue(), mime_type=image.type or "image/jpeg"
            )
        )
    contents.append(types.Content(role="user", parts=parts))

    try:
        r = generate(
            contents,
            types.GenerateContentConfig(system_instruction=system_prompt()),
        )
        return r.text or "Maaf karo, clear jawab nahi mila. Dobara try karo."
    except Exception as exc:  # noqa: BLE001
        debug_box.error(f"Gemini error: {exc}")
        return "Abhi service available nahi hai. Thodi der baad dobara try karo."


def parse_earning(message):
    prompt = f"""
Extract details from this gig-worker message.
Return JSON only with keys:
- platform: string
- amount: number (rupees earned), null if unclear
- expense: number (rupees), 0 if none mentioned
- expected_amount: number or null; only if the worker says they received
  less than the promised amount
- note: short string
Do not invent values.
Message: {message}
"""
    r = generate(
        prompt, types.GenerateContentConfig(response_mime_type="application/json")
    )
    data = json.loads(r.text)
    if not isinstance(data, dict):
        raise ValueError("bad format")

    platform = str(data.get("platform") or "").strip()
    if not platform or data.get("amount") is None:
        raise ValueError("missing fields")

    amount = float(data["amount"])
    expense = float(data.get("expense") or 0)
    expected = data.get("expected_amount")
    expected = float(expected) if expected is not None else None
    if amount < 0 or expense < 0 or (expected is not None and expected < 0):
        raise ValueError("negative")

    return {
        "platform": platform,
        "amount": amount,
        "expense": expense,
        "expected_amount": expected,
        "note": str(data.get("note") or "").strip(),
    }


# ---------- UI ----------
st.title("🤝 Saathi")
st.caption("Gig workers ka apna saathi: kamai, suraksha, haq aur shikayat")

tab_chat, tab_earn, tab_scheme, tab_doc, tab_grv = st.tabs(
    ["💬 Chat", "💰 Kamai", "🏛 Yojana", "📄 Document", "✍️ Shikayat"]
)

# ----- Chat -----
with tab_chat:
    st.session_state.setdefault("msgs", [])

    quick = None
    c1, c2, c3 = st.columns(3)
    if c1.button("🛵 Raat ki safety"):
        quick = "Raat ko delivery karte time safety ke liye kya dhyan rakhun?"
    if c2.button("⚖️ Mere haq"):
        quick = "Ek gig worker ke kaun se haq hote hain?"
    if c3.button("🏥 Health scheme"):
        quick = "Gig worker ke liye health insurance ki kaun si scheme hai?"

    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    question = st.chat_input("Kuch bhi poochho: safety, schemes, haq...") or quick
    if question:
        history = list(st.session_state.msgs)
        st.session_state.msgs.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Saathi soch raha hai..."):
                answer = ask(question, history)
            st.write(answer)
        st.session_state.msgs.append({"role": "assistant", "content": answer})

# ----- Earnings -----
with tab_earn:
    st.subheader("Aaj ki kamai")
    earning_text = st.text_input(
        "Aaj ki kamai likho",
        placeholder="Aaj Swiggy se 850 kamaye, petrol 200",
        key="earning_text",
    )
    st.caption(
        "Payment kam aaya? Aise likho: 'Uber ne 600 ki jagah 450 diye, petrol 150'"
    )

    if st.button("Save karo", key="save_earning") and earning_text.strip():
        try:
            with st.spinner("Details samajh raha hoon..."):
                e = parse_earning(earning_text)
            db.execute(
                "INSERT INTO earnings (uid, day, platform, amount, expense, note) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (UID, str(datetime.date.today()), e["platform"], e["amount"],
                 e["expense"], e["note"]),
            )
            db.commit()
            st.success(
                f"✅ {e['platform']}: ₹{e['amount']:.0f} kamai, "
                f"₹{e['expense']:.0f} kharcha"
            )

            exp = e["expected_amount"]
            if exp is not None and exp > e["amount"]:
                gap = exp - e["amount"]
                st.warning(f"⚠️ Bataye hisaab se ₹{gap:.0f} kam mile.")
                # Connected workflow: pre-fill the grievance form
                st.session_state["grievance_issue"] = (
                    f"{e['platform']} ne mujhe ₹{exp:.0f} ki jagah sirf "
                    f"₹{e['amount']:.0f} diye. {e['note']}"
                ).strip()
                st.session_state["grievance_draft"] = ""
                st.info("👉 Shikayat tab kholo, details pehle se bhari hain.")
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            st.error(
                "Details samajh nahi aayi. Platform aur kamai clearly likho, "
                "jaise: 'Aaj Swiggy se 850 kamaye, petrol 200'."
            )
        except Exception as exc:  # noqa: BLE001
            debug_box.error(f"Earnings error: {exc}")
            st.error("Kamai save nahi ho paayi. Debug box check karo.")

    df = pd.read_sql_query(
        "SELECT day, platform, amount, expense, note FROM earnings "
        "WHERE uid = ? ORDER BY day",
        db, params=(UID,),
    )

    if not df.empty:
        df["net"] = df["amount"] - df["expense"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Total kamai", f"₹{df['amount'].sum():.0f}")
        m2.metric("Kharcha", f"₹{df['expense'].sum():.0f}")
        m3.metric("Bachat", f"₹{df['net'].sum():.0f}")
        st.bar_chart(df.groupby("day")["net"].sum())
        with st.expander("Kamai records dekho"):
            st.dataframe(df, hide_index=True)
        if st.button("📊 Mera summary + tips", key="earnings_summary"):
            with st.spinner("Summary taiyar ho rahi hai..."):
                st.write(ask(
                    "Is earnings data ka simple summary do aur paise bachane "
                    "ki 2 practical tips do. Data:\n" + df.to_string(index=False)
                ))
    else:
        st.info("Abhi koi kamai save nahi hui hai.")

# ----- Schemes -----
with tab_scheme:
    st.subheader("Kaun si yojana mere liye hai?")
    with st.form("scheme_form"):
        age = st.number_input("Umar", min_value=14, max_value=80, value=28)
        state = st.text_input("Rajya (State)", placeholder="Punjab")
        work = st.selectbox(
            "Kaam ka type",
            ["Delivery partner", "Cab / auto driver", "Daily-wage / construction",
             "Street vendor", "Domestic worker", "Other"],
        )
        has_bank = st.checkbox("Mera bank account hai", value=True)
        submitted = st.form_submit_button("Yojana dhundo")

    if submitted:
        with st.spinner("Yojana dhundh raha hoon..."):
            st.write(ask(
                f"Worker profile: age {age}, state {state or 'not given'}, "
                f"work: {work}, bank account: {'yes' if has_bank else 'no'}. "
                "Suggest up to 4 possibly relevant Indian government schemes "
                "(e.g. e-Shram, Ayushman Bharat, PM-SYM, PM-SVANidhi). For each: "
                "one-line benefit and the next step to apply. Say clearly that "
                "eligibility must be confirmed on the official portal."
            ))

# ----- Documents -----
with tab_doc:
    st.subheader("Document samjho")
    uploaded = st.file_uploader(
        "ID, notice, ya payment screenshot ki photo upload karo",
        type=["png", "jpg", "jpeg"],
        key="document_upload",
    )
    if uploaded:
        st.image(uploaded, caption="Uploaded document", width=300)
        if st.button("Samjhao", key="explain_document"):
            with st.spinner("Document samajh raha hoon..."):
                st.write(ask(
                    "Is document mein kya likha hai, simple bhasha mein samjhao. "
                    "Koi deadline, amount ya next step ho to clearly batao. "
                    "Agar text padhne layak nahi hai, to batao.",
                    image=uploaded,
                ))
    st.caption(
        "Privacy tip: Aadhaar number, bank details aur OTP hide karke hi upload karo."
    )

# ----- Grievance -----
with tab_grv:
    st.subheader("Shikayat draft karo")
    st.session_state.setdefault("grievance_issue", "")
    st.session_state.setdefault("grievance_draft", "")

    issue = st.text_area(
        "Kya hua? (kab, kitna paisa, kisne)", height=120, key="grievance_issue"
    )
    recipient = st.selectbox(
        "Kisko bhejni hai?",
        ["Company support", "Labour department", "Consumer helpline (1915)"],
        key="grievance_recipient",
    )

    if st.button("Shikayat likho", key="write_grievance") and issue.strip():
        with st.spinner("Shikayat taiyar ho rahi hai..."):
            st.session_state["grievance_draft"] = ask(
                f"Write a short, polite complaint for {recipient}. Use only the "
                "facts supplied; do not invent dates, evidence or legal claims. "
                "Include a subject, the issue, the requested action and a "
                f"suggested submission channel. Problem details: {issue}"
            )

    if st.session_state["grievance_draft"]:
        st.text_area(
            "Tumhari shikayat (copy karo)",
            value=st.session_state["grievance_draft"],
            height=300,
        )
        st.caption("Bhejne se pehle details check kar lo.")

# ---------- Footer ----------
st.divider()
st.caption(
    "Saathi sirf general jaankari deta hai, legal advice nahi. Scheme eligibility "
    "aur complaint process official source se verify karein."
)
