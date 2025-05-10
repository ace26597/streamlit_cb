# app.py – Streamlit front‑end for the Deep Research Assistant
"""Streamlit application that combines file upload, agent‑based planning & execution,
web search via Brave API, and session persistence to deliver a deep‑research chatbot."""

from __future__ import annotations

import os
import streamlit as st
from datetime import datetime
from typing import Dict, List, Any

from session_manager import (
    list_sessions,
    load_session,
    save_session,
)
from file_utils import load_files
from agent_engine import generate_plan, run_agent

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Configuration & Secrets
# ----------------------------------------------------------------------------
# Store secrets via Streamlit → Settings → Secrets or environment variables.
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
BRAVE_API_KEY = st.secrets.get("BRAVE_API_KEY", os.getenv("BRAVE_API_KEY", ""))
if not OPENAI_API_KEY or not BRAVE_API_KEY:
    st.error("⚠️  Please set OPENAI_API_KEY and BRAVE_API_KEY in Streamlit secrets!")
    st.stop()

# Pass keys to the agent module (on first import they might not yet be set)
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["BRAVE_API_KEY"] = BRAVE_API_KEY

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Page layout
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Deep Research Assistant", layout="wide")
st.title("🔎 Deep Research Assistant")

# ────────────────────────────────────────────────────────────────────────────────
# 🗂 Session selection / creation
# ----------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[Dict[str, str]] = []
if "files" not in st.session_state:
    st.session_state.files: Dict[str, Any] = {}
if "current_session" not in st.session_state:
    st.session_state.current_session: str | None = None

with st.sidebar:
    st.header("Session")
    sessions = list_sessions()
    session_option = st.selectbox(
        "Load existing session or create new:",
        options=["(New Session)"] + sessions,
        index=0 if st.session_state.current_session is None else sessions.index(st.session_state.current_session)+1,
    )

    if session_option != "(New Session)" and session_option != st.session_state.current_session:
        # Switch session: load chat & files
        chat, files = load_session(session_option)
        st.session_state.chat_history = chat
        st.session_state.files = files
        st.session_state.current_session = session_option
        st.success(f"Loaded session: {session_option}")

    if st.button("💾 Save Session"):
        name = (
            st.session_state.current_session
            or datetime.now().strftime("session_%Y%m%d_%H%M%S")
        )
        save_session(name, st.session_state.chat_history, st.session_state.files)
        st.session_state.current_session = name
        st.success(f"Session saved as: {name}")

    st.markdown("---")
    uploaded = st.file_uploader(
        "Upload documents (PDF, DOCX, TXT, CSV)",
        type=["pdf", "docx", "txt", "csv"],
        accept_multiple_files=True,
        help="Uploaded files are only stored locally on this machine.",
    )
    if uploaded:
        new_content = load_files(uploaded)
        st.session_state.files.update(new_content)
        st.success(f"Added {len(uploaded)} document(s) to context")

# ────────────────────────────────────────────────────────────────────────────────
# 💬 Chat interface
# ----------------------------------------------------------------------------
# Display previous chat
for msg in st.session_state.chat_history:
    role = msg["role"]
    if role == "user":
        st.chat_message("🧑‍💻 User").write(msg["content"])
    else:
        st.chat_message("🤖 Assistant").write(msg["content"])

prompt = st.chat_input("Ask a research question…")
if prompt:
    # 1️⃣  Show user message
    st.chat_message("🧑‍💻 User").write(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # 2️⃣  Generate research plan
    plan_steps = generate_plan(prompt, st.session_state.files)
    plan_md = "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan_steps)])
    st.chat_message("📑 Plan").markdown(plan_md)

    # 3️⃣  Execute agent
    with st.chat_message("🤖 Assistant"):
        answer, sources = run_agent(prompt, st.session_state)
        st.markdown(answer)
        if sources:
            st.markdown("**Sources:**")
            for s in sources:
                st.markdown(f"- <{s}>")

    # 4️⃣  Store assistant answer
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # 5️⃣  Autosave current session (optional)
    autosave_name = st.session_state.current_session or "autosave_latest"
    save_session(autosave_name, st.session_state.chat_history, st.session_state.files)
