import json
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types

st.set_page_config(page_title="Saathi | Gig Worker Companion", page_icon="🤝", layout="centered")

# ---------------- Styling ----------------
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 1.5rem; max-width: 820px;}

.hero {
  background: linear-gradient(135deg, #0b8f5a 0%, #12b886 55%, #3bc9db 100%);
  border-radius: 20px; padding: 28px 30px; color: #fff;
  box-shadow: 0 10px 30px rgba(18,184,134,.25); margin-bottom: 18px;
}
.hero h1 {margin: 0; font-size: 2.2rem; color: #fff;}
.hero p {margin: 6px 0 14px 0; font-size: 1.05rem; opacity: .95;}
.chip {
  display: inline-block; background: rgba(255,255,255,.2); border-radius: 999px;
  padding: 4px 12px; margin: 0 6px 6px 0; font-size: .82rem; font-weight: 600;
}

.fcard {
  background: #fff; border: 1px solid #e9ecef; border-radius: 16px;
  padding: 16px; text-align: center; height: 100%;
  box-shadow: 0 2px 10px rgba(0,0,0,.04);
}
.fcard .ic {font-size: 1.8rem;}
.fcard b {display: block; margin: 6px 0 2px 0; color: #1a1a1a;}
.fcard span {font-size: .82rem; color: #6c757d;}

[data-testid="stMetric"] {
  background: #fff; border: 1px solid #e9ecef; border-radius: 14px;
  padding: 14px 16px; box-shadow: 0 2px 10px rgba(0,0,0,.04);
}
.stTabs [data-baseweb="tab-list"] {gap: 6px;}
.stTabs [data-baseweb="tab"] {
  background: #f1f3f5; border-radius: 10px 10px 0 0; padding: 8px 14px;
}
.stTabs [aria-selected="true"] {background: #12b886 !important; color: #fff !important;}
.stButton > button {
  border-radius: 10px; font-weight: 600; border: 1px solid #12b886;
}
.stButton > button:hover {background: #12b886; color: #fff; border-color: #12b886;}
.sec-title {font-size: 1.15rem; font-weight: 700; margin: 4px 0 8px 0;}
.disclaimer {text-align: center; color: #868e96; font-size: .8rem; margin-top: 8px;}
</style>
""", unsafe_allow_html=True)

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

# ---------------- Hero ----------------
st.markdown("""
<div class="hero">
  <h1>🤝 Saathi</h1>
  <p>Delivery partners, drivers aur daily-wage workers ka apna AI saathi</p>
  <span class="chip">🌐 8 Languages</span>
  <span class="chip">✨ Powered by
