"""Simple JSON file–based persistence for chat sessions."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

SESSION_DIR = Path("saved_sessions")
SESSION_DIR.mkdir(exist_ok=True)

ChatHistory = List[Dict[str, str]]
FilesDict = Dict[str, Any]


def _file_path(name: str) -> Path:
    return SESSION_DIR / f"{name}.json"


def save_session(name: str, chat_history: ChatHistory, files: FilesDict) -> None:
    data = {
        "chat_history": chat_history,
        "files": {k: (v if isinstance(v, str) else "<dataframe>") for k, v in files.items()},
    }
    with open(_file_path(name), "w", encoding="utf-8") as fp:
        json.dump(data, fp)


def load_session(name: str) -> Tuple[ChatHistory, FilesDict]:
    path = _file_path(name)
    if not path.exists():
        return [], {}
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    # Note: DataFrames cannot be round‑tripped easily to JSON without extra work.
    # Here we return strings for simplicity. Real app might use parquet for DataFrames.
    return data.get("chat_history", []), data.get("files", {})


def list_sessions() -> List[str]:
    return [p.stem for p in SESSION_DIR.glob("*.json")]
