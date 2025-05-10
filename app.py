# app.py – Streamlit front‑end for the Deep Research Assistant
"""Streamlit application that combines file upload, agent‑based planning & execution,
web search via Brave API, and session persistence to deliver a deep‑research chatbot."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List, Any

import streamlit as st

from session_manager import list_sessions, load_session, save_session
from file_utils import load_files
from agent_engine import generate_plan, run_agent

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Configuration & Secrets
# ────────────────────────────────────────────────────────────────────────────────
# Store secrets via Streamlit → Settings → Secrets or environment variables.
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
BRAVE_API_KEY = st.secrets.get("BRAVE_API_KEY", os.getenv("BRAVE_API_KEY", ""))
if not OPENAI_API_KEY or not BRAVE_API_KEY:
    st.error("⚠️  Please set OPENAI_API_KEY and BRAVE_API_KEY in Streamlit secrets!")
    st.stop()

# Pass keys to agent modules
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["BRAVE_API_KEY"] = BRAVE_API_KEY

# ────────────────────────────────────────────────────────────────────────────────
# 🎨 Page layout
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Deep Research Assistant", layout="wide")
st.title("🔎 Deep Research Assistant")

# ────────────────────────────────────────────────────────────────────────────────
# 🗂 Session state init
# ────────────────────────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[Dict[str, str]] = []
if "files" not in st.session_state:
    st.session_state.files: Dict[str, Any] = {}
if "current_session" not in st.session_state:
    st.session_state.current_session: str | None = None

# ────────────────────────────────────────────────────────────────────────────────
# 📁 Sidebar – session management & file upload
# ────────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Session")
    sessions = list_sessions()
    default_idx = 0 if st.session_state.current_session is None else sessions.index(st.session_state.current_session) + 1
    session_option = st.selectbox(
        "Load existing session or create new:",
        options=["(New Session)"] + sessions,
        index=default_idx,
    )

    if session_option != "(New Session)" and session_option != st.session_state.current_session:
        chat, files = load_session(session_option)
        st.session_state.chat_history = chat
        st.session_state.files = files
        st.session_state.current_session = session_option
        st.success(f"Loaded session: {session_option}")

    if st.button("💾 Save Session"):
        name = st.session_state.current_session or datetime.now().strftime("session_%Y%m%d_%H%M%S")
        save_session(name, st.session_state.chat_history, st.session_state.files)
        st.session_state.current_session = name
        st.success(f"Session saved as: {name}")

    st.markdown("---")
    uploaded_files = st.file_uploader(
        "Upload documents (PDF, DOCX, TXT, CSV)",
        type=["pdf", "docx", "txt", "csv"],
        accept_multiple_files=True,
        help="Files stay local on this machine only.",
    )
    if uploaded_files:
        new_content = load_files(uploaded_files)
        st.session_state.files.update(new_content)
        st.success(f"Added {len(uploaded_files)} document(s) to context")

# ────────────────────────────────────────────────────────────────────────────────
# 💬 Chat interface
# ────────────────────────────────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    role = "🧑‍💻 User" if msg["role"] == "user" else "🤖 Assistant"
    st.chat_message(role).write(msg["content"])

prompt = st.chat_input("Ask a research question…")
if prompt:
    # 1️⃣  Echo user message
    st.chat_message("🧑‍💻 User").write(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # 2️⃣  Generate & show plan
    plan_steps = generate_plan(prompt, st.session_state.files)
    plan_md = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan_steps))
    st.chat_message("📑 Plan").markdown(plan_md)

    # 3️⃣  Run agent & display answer
    with st.chat_message("🤖 Assistant"):
        answer, sources = run_agent(prompt, st.session_state)
        st.markdown(answer)
        if sources:
            st.markdown("**Sources:**")
            for link in sources:
                st.markdown(f"- <{link}>")

    # 4️⃣  Store assistant response
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # 5️⃣  Auto‑save session
    autosave = st.session_state.current_session or "autosave_latest"
    save_session(autosave, st.session_state.chat_history, st.session_state.files)
