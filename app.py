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

MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]  # fallback order


# ---------- Gemini client ----------
def get_api_key():
    try:
        return str(st.secrets["GEMINI_API_KEY"]).strip()
    except Exception:
        return (os.environ.get("GEMINI_API_KEY") or "").strip()


@st.cache_resource
def get_client(api_key: str):
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


# ---------- Database (per-user rows)
