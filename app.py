# app.py (Streamlit main script)
import streamlit as st
from datetime import datetime
import json
# Import our modules (assuming they are implemented separately)
from file_utils import load_files
from agent import research_agent, generate_plan
from session_manager import save_session, load_session

st.set_page_config(page_title="Deep Research Assistant", layout="wide")
st.title("🔎 Deep Research Assistant")

# Sidebar: Session selection and File uploads
session_names = load_session.list_sessions()  # e.g., returns list of saved session IDs or names
session_choice = st.sidebar.selectbox("Load a previous session", options=["(New Session)"] + session_names)
if session_choice and session_choice != "(New Session)":
    # Load the selected session data (chat history, files)
    st.session_state['chat_history'], st.session_state['files'] = load_session(session_choice)

uploaded_files = st.sidebar.file_uploader("Upload documents (PDF, DOCX, TXT, CSV)", 
                                         type=["pdf", "docx", "txt", "csv"], 
                                         accept_multiple_files=True)
if uploaded_files:
    # Read and store file contents
    files_content = load_files(uploaded_files)
    st.session_state.setdefault('files', {}).update(files_content)  # store in session state

# Main area: Chat interface
user_query = st.text_input("Ask a research question:", "")
if user_query:
    # Process the query when submitted
    # (Agent planning and execution will happen here, see below)
    pass  # placeholder for the agent call
