import os, json, sqlite3, datetime
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

st.set_page_config(page_title="Saathi", page_icon="🤝", layout="centered")

# ---------- API key ----------
API_KEY = "AIzaSyCC0RyZVowo93En_AeNzxBf81mgX4ufvNE"

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

# ---------- DB ----------
db = sqlite3.connect("saathi.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS earnings(
    day TEXT, platform TEXT, amount REAL, expense REAL, note TEXT)""")

# ---------- Gemini helpers ----------
LANGS = ["Hinglish", "Hindi", "English", "Marathi", "Tamil", "Telugu", "Bengali", "Kannada"]
lang = st.sidebar.selectbox("🌐 Bhasha / Language", LANGS)

def system_prompt():
    return f"""You are Saathi, a friendly assistant for gig and informal workers in India
(delivery partners, drivers, daily-wage workers).
- Reply in {lang}, in very simple words and short sentences.
- Topics: earnings, safety practices, rights and welfare schemes
  (e-Shram, Ayushman Bharat, PM-SVANidhi, PM-SYM, Code on Social Security 2020),
  document help, grievance drafting.
- For schemes: ask 2-3 short questions (age, state, work type), then suggest
  eligible schemes and next steps.
- Never give legal guarantees. If unsure, suggest a helpline or legal aid.
- Keep answers under 150 words unless asked for more."""

def ask(prompt, history=None, image=None):
    contents = []
    for m in (history or []):
        contents.append(types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])]))
    parts = [types.Part(text=prompt)]
    if image:
        parts.append(types.Part.from_bytes(data=image.getvalue(), mime_type=image.type))
    contents.append(types.Content(role="user", parts=parts))
    try:
        r = client.models.generate_content(
            model=MODEL, contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_prompt()))
        return r.text
    except Exception as e:
        return f"⚠️ Kuch gadbad hui, dobara try karo. ({e})"

def parse_earning(text):
    prompt = f"""Extract from this gig worker message: platform (string),
amount earned (number, rupees), expense (number, rupees, 0 if none),
expected_amount (number or null; fill only if they say payment was less than promised),
note (short string). Return JSON only with keys:
platform, amount, expense, expected_amount, note.
Message: {text}"""
    r = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"))
    return json.loads(r.text)

# ---------- UI ----------
st.title("🤝 Saathi")
st.caption("Gig workers ka apna saathi: kamai, suraksha, haq aur shikayat")

tab_chat, tab_earn, tab_doc, tab_grv = st.tabs(
    ["💬 Chat", "💰 Kamai", "📄 Document", "✍️ Shikayat"])

# ----- Chat -----
with tab_chat:
    st.session_state.setdefault("msgs", [])
    for m in st.session_state.msgs:
        st.chat_message(m["role"]).write(m["content"])
    q = st.chat_input("Kuch bhi poochho: safety, schemes, haq...")
    if q:
        st.chat_message("user").write(q)
        ans = ask(q, st.session_state.msgs)
        st.session_state.msgs += [{"role": "user", "content": q},
                                  {"role": "assistant", "content": ans}]
        st.chat_message("assistant").write(ans)

# ----- Earnings -----
with tab_earn:
    txt = st.text_input("Aaj ki kamai likho",
                        placeholder="Aaj Swiggy se 850 kamaye, petrol 200")
    if st.button("Save karo") and txt:
        try:
            d = parse_earning(txt)
            db.execute("INSERT INTO earnings VALUES(?,?,?,?,?)",
                       (str(datetime.date.today()), d["platform"], d["amount"],
                        d.get("expense") or 0, d.get("note", "")))
            db.commit()
            st.success(f"✅ {d['platform']}: ₹{d['amount']} kamai, ₹{d.get('expense') or 0} kharcha")
            if d.get("expected_amount") and d["expected_amount"] > d["amount"]:
                gap = d["expected_amount"] - d["amount"]
                st.warning(f"⚠️ ₹{gap} kam mile lag rahe hain.")
                st.session_state.prefill = (
                    f"{d['platform']} ne mujhe ₹{d['expected_amount']} ki jagah "
                    f"sirf ₹{d['amount']} diye. {d.get('note', '')}")
                st.info("Shikayat tab mein jao, draft ready hai 👉")
        except Exception:
            st.error("Samajh nahi aaya, dobara likho (platform aur amount ke saath).")

    df = pd.read_sql("SELECT * FROM earnings", db)
    if not df.empty:
        df["net"] = df["amount"] - df["expense"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total kamai", f"₹{df.amount.sum():.0f}")
        c2.metric("Kharcha", f"₹{df.expense.sum():.0f}")
        c3.metric("Bachat", f"₹{df.net.sum():.0f}")
        st.bar_chart(df.groupby("day")["net"].sum())
        if st.button("📊 Mera summary + tips"):
            st.write(ask("Is earnings data ka simple summary do aur 2 paise bachane "
                         "ki tips do:\n" + df.to_string(index=False)))

# ----- Documents -----
with tab_doc:
    f = st.file_uploader("ID, notice, ya payment screenshot ki photo",
                         type=["png", "jpg", "jpeg"])
    if f:
        st.image(f, width=250)
        if st.button("Samjhao"):
            st.write(ask("Is document mein kya likha hai, simple bhasha mein samjhao. "
                         "Mujhe kya karna chahiye? Koi deadline ya paisa ho to batao.",
                         image=f))

# ----- Grievance -----
with tab_grv:
    issue = st.text_area("Kya hua? (kab, kitna paisa, kisne)",
                         value=st.session_state.get("prefill", ""), height=120)
    to = st.selectbox("Kisko bhejni hai?",
                      ["Company support", "Labour department", "Consumer helpline (1915)"])
    if st.button("Shikayat likho") and issue:
        draft = ask(f"Ye shikayat likho, polite aur chhoti, '{to}' ke liye, "
                    f"is problem par: {issue}. Subject line, date, aur maange gaye "
                    f"action ke saath. Aakhir mein batao kahan bhejni hai.")
        st.text_area("Tumhari shikayat (copy karo)", draft, height=300)
