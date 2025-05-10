"""Utility functions for reading uploaded files into usable text or DataFrame objects."""
from __future__ import annotations

import io
from typing import Dict, Any

import pandas as pd
from PyPDF2 import PdfReader
from docx import Document

# -----------------------------------------------------------------------------
# 🔍 File loaders
# -----------------------------------------------------------------------------

def load_files(uploaded_files) -> Dict[str, Any]:
    """Return a mapping {filename: content} for a list of Streamlit UploadedFile."""
    content = {}
    for f in uploaded_files:
        name = f.name
        if name.lower().endswith(".pdf"):
            text = _read_pdf(f)
            content[name] = text
        elif name.lower().endswith(".docx"):
            text = _read_docx(f)
            content[name] = text
        elif name.lower().endswith(".csv"):
            df = pd.read_csv(f)
            content[name] = df
        else:
            # Assume plain text
            data = f.getvalue().decode("utf-8", errors="ignore")
            content[name] = data
    return content


def _read_pdf(uploaded_file) -> str:
    reader = PdfReader(uploaded_file)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _read_docx(uploaded_file) -> str:
    doc = Document(uploaded_file)
    paras = [p.text for p in doc.paragraphs]
    return "\n".join(paras)
