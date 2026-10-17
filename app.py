import json
import sqlite3
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ---------- Page setup ----------
st.set_page_config(
    page_title="Saathi | Gig Worker Companion",
    page_icon="🤝",
    layout="centered",
)

# ---------- API key / Gemini ----------
# Add this in Streamlit Cloud: App settings -> Secrets
# GEMINI_API_KEY = "your-new-api-key"
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    st.error(
        "Gemini API key nahi mili. Streamlit Cloud mein "
        "App settings → Secrets ke andar GEMINI_API_KEY set karo."
    )
    st.stop()

MODEL = "gemini-2.5-flash"

# ---------- Database ----------
# Note: Streamlit Cloud's local filesystem may not be durable across redeploys.
DB_PATH = Path("saathi.db")
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute(
    """
    CREATE TABLE IF NOT EXISTS earnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        platform TEXT NOT NULL,
        amount REAL NOT NULL,
        expense REAL NOT NULL DEFAULT 0,
        note TEXT DEFAULT ''
    )
    """
)
db.commit()

# ---------- Language ----------
LANGS = [
    "Hinglish", "Hindi", "English", "Marathi",
    "Tamil", "Telugu", "Bengali", "Kannada"
]
lang = st.sidebar.selectbox("🌐 Bhasha / Language", LANGS)


def system_prompt():
    return f"""
You are Saathi, a friendly assistant for gig and informal workers in India
(delivery partners, drivers, and daily-wage workers).
- Reply in {lang}, using very simple words and short sentences.
- Help with earnings, safety practices, rights and welfare schemes
  (e-Shram, Ayushman Bharat, PM-SVANidhi, PM-SYM, and applicable labour rules),
  document explanation, and grievance drafting.
- For scheme eligibility, ask up to 2-3 short questions such as age, state,
  and type of work before suggesting possible options.
- Do not guarantee eligibility or legal outcomes.
- For uncertain or urgent matters, recommend checking the official government
  source or an appropriate helpline/legal-aid service.
- Keep answers under 150 words unless the user asks for more.
"""


def ask(prompt, history=None, image=None):
    """Send a prompt and optional chat history/image to Gemini."""
    contents = []

    for message in history or []:
        role = "user" if message.get("role") == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=str(message.get("content", "")))],
            )
        )

    parts = [types.Part(text=prompt)]
    if image is not None:
        image_bytes = image.getvalue()
        mime_type = image.type or "image/jpeg"
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    contents.append(types.Content(role="user", parts=parts))

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt()
            ),
        )
        if not response.text:
            return "Maaf karo, mujhe is baar clear jawab nahi mila. Dobara try karo."
        return response.text
    except Exception as exc:
        # Avoid displaying secrets or extensive internal details to app users.
        st.error(
            "Gemini se response nahi aa paya. API key, model access, "
            "internet connection aur Streamlit logs check karo."
        )
        return "Abhi service available nahi hai. Thodi der baad dobara try karo."


def parse_earning(message):
    """Extract earning details and validate the AI response."""
    prompt = f"""
Extract details from this gig-worker message.
Return JSON only with these keys:
- platform: string
- amount: number, amount earned in rupees
- expense: number, expenses in rupees (0 if none mentioned)
- expected_amount: number or null; only when the worker explicitly says
  they received less than the promised amount
- note: short string

Do not invent values. If the amount earned is unclear, return amount as null.
Message: {message}
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    if not response.text:
        raise ValueError("Empty response")

    data = json.loads(response.text)
    if not isinstance(data, dict):
        raise ValueError("Unexpected response format")

    platform = str(data.get("platform") or "").strip()
    if not platform:
        raise ValueError("Platform missing")

    if data.get("amount") is None:
        raise ValueError("Amount missing")

    amount = float(data["amount"])
    expense = float(data.get("expense") or 0)
    expected = data.get("expected_amount")

    if amount < 0 or expense < 0:
        raise ValueError("Amounts cannot be negative")

    if expected is not None:
        expected = float(expected)
        if expected < 0:
            raise ValueError("Expected amount cannot be negative")

    return {
        "platform": platform,
        "amount": amount,
        "expense": expense,
        "expected_amount": expected,
        "note": str(data.get("note") or "").strip(),
    }


# ---------- App UI ----------
st.title("🤝 Saathi")
st.caption(
    "Gig workers ka apna saathi: kamai, suraksha, haq aur shikayat"
)

tab_chat, tab_earn, tab_doc, tab_grv = st.tabs(
    ["💬 Chat", "💰 Kamai", "📄 Document", "✍️ Shikayat"]
)

# ----- Chat -----
with tab_chat:
    st.session_state.setdefault("msgs", [])

    for message in st.session_state.msgs:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input(
        "Kuch bhi poochho: safety, schemes, haq..."
    )

    if question:
        st.session_state.msgs.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Saathi soch raha hai..."):
                answer = ask(question, st.session_state.msgs[:-1])
            st.write(answer)

        st.session_state.msgs.append(
            {"role": "assistant", "content": answer}
        )

# ----- Earnings -----
with tab_earn:
    st.subheader("Aaj ki kamai")
    earning_text = st.text_input(
        "Aaj ki kamai likho",
        placeholder="Aaj Swiggy se 850 kamaye, petrol 200",
        key="earning_text",
    )

    if st.button("Save karo", key="save_earning") and earning_text.strip():
        try:
            with st.spinner("Kamai details samajh raha hoon..."):
                earning = parse_earning(earning_text)

            today = str(datetime.date.today())
            db.execute(
                """
                INSERT INTO earnings (day, platform, amount, expense, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    today,
                    earning["platform"],
                    earning["amount"],
                    earning["expense"],
                    earning["note"],
                ),
            )
            db.commit()

            st.success(
                f"✅ {earning['platform']}: ₹{earning['amount']:.0f} kamai, "
                f"₹{earning['expense']:.0f} kharcha"
            )

            expected = earning["expected_amount"]
            if expected is not None and expected > earning["amount"]:
                gap = expected - earning["amount"]
                st.warning(f"⚠️ Bataye gaye hisaab se ₹{gap:.0f} kam mile.")
                st.session_state["prefill"] = (
                    f"{earning['platform']} ne mujhe ₹{expected:.0f} ki jagah "
                    f"sirf ₹{earning['amount']:.0f} diye. "
                    f"{earning['note']}"
                )
                st.info(
                    "Shikayat tab kholo. Wahan issue text mein yeh draft "
                    "karne ke liye details mil jayengi."
                )

        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            st.error(
                "Details samajh nahi aayi. Platform aur kamai clearly likho, "
                "jaise: 'Aaj Swiggy se 850 kamaye, petrol 200'."
            )
        except Exception:
            st.error(
                "Kamai save nahi ho paayi. API access aur app logs check karo."
            )

    df = pd.read_sql_query(
        "SELECT day, platform, amount, expense, note FROM earnings ORDER BY day",
        db,
    )

    if not df.empty:
        df["net"] = df["amount"] - df["expense"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total kamai", f"₹{df['amount'].sum():.0f}")
        col2.metric("Kharcha", f"₹{df['expense'].sum():.0f}")
        col3.metric("Bachat", f"₹{df['net'].sum():.0f}")

        st.bar_chart(df.groupby("day")["net"].sum())
        with st.expander("Kamai records dekho"):
            st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("📊 Mera summary + tips", key="earnings_summary"):
            with st.spinner("Summary taiyar ho rahi hai..."):
                summary = ask(
                    "Is earnings data ka simple summary do aur paise bachane "
                    "ki 2 practical tips do. Data:\n"
                    + df.to_string(index=False)
                )
            st.write(summary)
    else:
        st.info("Abhi koi kamai save nahi hui hai.")

# ----- Documents -----
with tab_doc:
    st.subheader("Document samjho")
    uploaded_file = st.file_uploader(
        "ID, notice, ya payment screenshot ki photo upload karo",
        type=["png", "jpg", "jpeg"],
        key="document_upload",
    )

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded document", width=300)
        if st.button("Samjhao", key="explain_document"):
            with st.spinner("Document samajh raha hoon..."):
                explanation = ask(
                    "Is document mein kya likha hai, simple bhasha mein samjhao. "
                    "Koi deadline, amount, ya next step ho to clearly batao. "
                    "Agar text padhne layak nahi hai, to batao.",
                    image=uploaded_file,
                )
            st.write(explanation)

    st.caption(
        "Privacy tip: Aadhaar number, bank details, OTP aur doosri sensitive "
        "jaankari share karne se pehle hide kar do."
    )

# ----- Grievance -----
with tab_grv:
    st.subheader("Shikayat draft karo")

    st.session_state.setdefault("prefill", "")
    st.session_state.setdefault("grievance_draft", "")

    if st.session_state.get("prefill"):
        if st.button("Kamai wale issue ka text use karo", key="use_prefill"):
            st.session_state["grievance_issue"] = st.session_state["prefill"]
            st.session_state["prefill"] = ""
            st.session_state["grievance_draft"] = ""

    issue = st.text_area(
        "Kya hua? (kab, kitna paisa, kisne)",
        value=st.session_state.get("prefill", ""),
        height=120,
        key="grievance_issue",
    )

    recipient = st.selectbox(
        "Kisko bhejni hai?",
        [
            "Company support",
            "Labour department",
            "Consumer helpline (1915)",
        ],
        key="grievance_recipient",
    )

    if st.button("Shikayat likho", key="write_grievance") and issue.strip():
        with st.spinner("Shikayat taiyar ho rahi hai..."):
            st.session_state["grievance_draft"] = ask(
                f"Write a short, polite complaint for {recipient}. "
                f"Use only the facts supplied; do not invent a date, evidence, "
                f"or legal claim. Include a subject, the issue, the requested "
                f"action, and a suggested submission channel. "
                f"Problem details: {issue}"
            )

    if st.session_state.get("grievance_draft"):
        st.text_area(
            "Tumhari shikayat (copy karo)",
            value=st.session_state["grievance_draft"],
            height=300,
            key="grievance_draft_display",
        )
        st.caption("Text select karke Ctrl+C dabao. Bhejne se pehle details check karo.")

# ---------- Footer ----------
st.divider()
st.caption(
    "Saathi informational help deta hai. Scheme eligibility aur official "
    "complaint process ko relevant government/company source se verify karein."
)
