from __future__ import annotations
import os, requests
from typing import List, Dict, Any

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

def chat_ollama(messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    """
    messages: [{'role':'system'|'user'|'assistant', 'content':'...'}]
    Returns assistant text using Ollama /api/chat.
    """
    url = f"{OLLAMA_BASE}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {
            "temperature": temperature,
        },
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("message", {}).get("content", "").strip()
