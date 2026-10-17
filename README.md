# Saathi 🤝: Gig Worker Companion

A GenAI-powered assistant for gig and informal workers in India
(delivery partners, drivers, daily-wage workers). Built for the
**Google for Developers PromptWars: Warm-up Challenge**.

## Problem
Gig workers often struggle to track earnings, know their rights,
find welfare schemes, understand documents, and write complaints,
especially when information is not in their language or simple words.

## Solution
Saathi uses Gemini as the core engine to give simple, multilingual
guidance in one app with connected workflows.

## Features
| Feature | What it does |
|---|---|
| 💬 Chat assistant | Answers on safety, rights and welfare schemes (e-Shram, Ayushman Bharat, PM-SVANidhi, PM-SYM) in simple language |
| 💰 Earnings tracker | Type "Aaj Swiggy se 850 kamaye, petrol 200"; Gemini extracts platform, amount and expense into structured data and shows totals, a chart and savings tips |
| 📄 Document help | Upload a photo of an ID, notice or payment screenshot; Gemini explains it simply and flags deadlines or amounts |
| ✍️ Grievance drafting | Describe the problem; get a short, polite complaint addressed to the company, labour department or consumer helpline |
| 🌐 Multilingual | Hinglish, Hindi, English, Marathi, Tamil, Telugu, Bengali, Kannada |

## Connected workflow
If a user logs that a payment came in lower than promised, the app
detects the gap, warns them, and pre-fills the Grievance tab with a
ready draft, so earnings, rights and dispute help work as one flow.

## Tech stack
- Python, Streamlit
- Google Gemini API (`google-genai`), text, JSON extraction and image understanding
- SQLite for earnings storage
- Pandas for summaries and charts

## Run locally
```bash
git clone https://github.com/YOUR-USERNAME/saathi-gig-worker-companion.git
cd saathi-gig-worker-companion
pip install -r requirements.txt
mkdir .streamlit
echo 'GEMINI_API_KEY = "your-key"' > .streamlit/secrets.toml
streamlit run app.py
```

## Deploy
Deployed on Streamlit Community Cloud. The API key is stored in
App settings → Secrets as `GEMINI_API_KEY`.

## Limitations and future scope
- Voice input/output for low-literacy users
- State-wise scheme database with live eligibility checks
- Per-user login so each worker keeps a private earnings history
- WhatsApp bot version
- Responses are guidance, not legal advice

## Disclaimer
Saathi gives general information only. For legal matters, contact
a labour department office or legal aid service.
