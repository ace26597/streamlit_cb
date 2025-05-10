"""Agent setup: plan generation + execution with LangChain tools."""
from __future__ import annotations

import os
from typing import Dict, Any, List, Tuple

import openai
from langchain.chat_models import ChatOpenAI
from langchain.agents import (
    AgentType,
    Tool,
    initialize_agent,
)
from langchain.memory import ConversationBufferMemory

# Environment keys should be set by app.py before import
openai.api_key = os.getenv("OPENAI_API_KEY", "")

# ----------------------------------------------------------------------------
# 🛠 Brave Search Tool
# ----------------------------------------------------------------------------
import requests

BRAVE_API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

def brave_search(query: str, count: int = 5) -> str:
    """Return formatted text of top Brave search results."""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query, "count": count}
    r = requests.get(BRAVE_API_ENDPOINT, headers=headers, params=params, timeout=30)
    if r.status_code != 200:
        return f"(Brave search failed: {r.status_code})"
    data = r.json()
    results = data.get("web", {}).get("results", [])
    lines = []
    for res in results:
        title = res.get("title")
        desc = res.get("description")
        url = res.get("url")
        lines.append(f"{title}\n{desc}\n{url}\n")
    return "\n".join(lines)

# ----------------------------------------------------------------------------
# 🔎 Document search tool (simple keyword search)
# ----------------------------------------------------------------------------

def build_document_search(files: Dict[str, Any]):
    """Return a callable that searches the provided file contents."""
    def _search_documents(query: str) -> str:
        query_lower = query.lower()
        snippets: List[str] = []
        for name, content in files.items():
            if isinstance(content, str):
                if query_lower in content.lower():
                    idx = content.lower().find(query_lower)
                    snippet = content[max(0, idx - 120) : idx + 400]
                    snippets.append(f"From {name}: …{snippet}…")
            else:
                # DataFrame: convert to CSV text
                csv_text = content.to_csv(index=False)
                if query_lower in csv_text.lower():
                    snippets.append(f"Query found in DataFrame {name} (omitted for brevity)")
        return "\n".join(snippets) if snippets else "No match in uploaded documents."

    return _search_documents

# ----------------------------------------------------------------------------
# 🧠 Memory & LLM
# ----------------------------------------------------------------------------
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

# ----------------------------------------------------------------------------
# 📑 Plan generation (visible to user)
# ----------------------------------------------------------------------------

def generate_plan(question: str, files: Dict[str, Any] | None = None) -> List[str]:
    file_note = (
        f"The user provided files: {', '.join(files.keys())}. " if files else ""
    )
    prompt = (
        f"{file_note}Using numbered steps, outline a concise research plan to answer: '{question}'. "
        "Include actions such as web search, reading uploaded documents, summarizing, and analysis."
    )
    resp = llm([{"role": "user", "content": prompt}])
    text = resp.content.strip()
    steps = [s.strip("- ") for s in text.split("\n") if s.strip()]
    return steps

# ----------------------------------------------------------------------------
# 🤖 Agent execution
# ----------------------------------------------------------------------------
_agent_cache: Dict[str, Any] = {}

def _get_agent(files: Dict[str, Any]):
    """Return (and cache) a LangChain agent configured with the current files."""
    cache_key = str(sorted(files.keys()))
    if cache_key in _agent_cache:
        return _agent_cache[cache_key]

    # Build document search tool specific to current files
    doc_search_tool = Tool(
        name="document_search",
        func=build_document_search(files),
        description="Search the user's uploaded documents for relevant passages.",
    )
    web_tool = Tool(
        name="web_search",
        func=lambda q: brave_search(q, 5),
        description="Search the web (Brave) for up‑to‑date information.",
    )

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    agent = initialize_agent(
        tools=[web_tool, doc_search_tool],
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=False,
    )
    _agent_cache[cache_key] = agent
    return agent


def run_agent(question: str, st_state) -> Tuple[str, List[str]]:
    """Run the agent on the question. Return (answer_markdown, source_links)."""
    files = st_state.get("files", {})
    agent = _get_agent(files)

    # Preload memory with past chat
    for m in st_state.get("chat_history", []):
        role = m["role"]
        if role == "user":
            agent.memory.chat_memory.add_user_message(m["content"])
        else:
            agent.memory.chat_memory.add_ai_message(m["content"])

    answer: str = agent.run(question)

    # Rudimentary extraction of URLs from answer for citation list
    import re

    urls = re.findall(r"https?://\S+", answer)
    unique_urls: List[str] = sorted(set(urls))[:5]  # cap at 5
    return answer, unique_urls
