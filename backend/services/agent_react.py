# backend/services/agent_react.py
from __future__ import annotations
from typing import List, Dict, Any
import os, requests, json, re
from sqlalchemy.orm import Session

from .agent import (
    _load_application_bundle,
    _summarize_docs,
    _explain_decision,
)

# ---- Ollama config ----
OLLAMA_BASE = os.getenv("OLLAMA_URL", os.getenv("OLLAMA_BASE", "http://ollama:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SYSTEM_PROMPT = """
You are an expert financial underwriting assistant.

You must either:
  A) ANSWER directly to the user, or
  B) If you need structured data from tools, EMIT one or more JSON-only tool calls (one per line), e.g.:

{"tool": "<tool_name>", "args": {...}}
{"tool": "<tool_name>", "args": {...}}

Available tools (aliases allowed):
- decision_overview / explain_decision : Summarize latest decision and why.
- docs_summary / summarize_documents  : Summarize uploaded documents.

IMPORTANT:
- If you call tools, reply with JSON object(s) ONLY (no extra text).
- Do NOT include chain-of-thought; keep answers concise and clear.
"""

# -------------------------------------------------------------------
# Ollama chat
# -------------------------------------------------------------------
def _ollama_chat(messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    url = f"{OLLAMA_BASE}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return (data.get("message", {}) or {}).get("content", "").strip()

# -------------------------------------------------------------------
# Robust tool-call extraction (JSON / JSONL / arrays / fenced)
# -------------------------------------------------------------------
_CODE_FENCE_RE = re.compile(r"```(?:json|jsonl|tool)?\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)

def _strip_code_fences(s: str) -> str:
    """
    Remove ```json/``` blocks but keep their inner content.
    If multiple fenced blocks exist, join inner content and append any tail text.
    """
    blocks = _CODE_FENCE_RE.findall(s)
    if blocks:
        inner = "\n".join(b.strip() for b in blocks if b is not None)
        tail = _CODE_FENCE_RE.sub("", s).strip()
        return f"{inner}\n{tail}".strip() if tail else inner
    return s

def _extract_tool_json_objects(mixed: str) -> List[Dict[str, Any]]:
    """
    Accepts:
      - Single JSON object            -> {"tool": "...", "args": {...}}
      - JSON array of tool calls      -> [{"tool": ...}, ...]
      - JSONL (one object per line)
      - Mixed narration + JSON (with or without ```json fences)
    Returns a list of dicts (each has a "tool" key), preserving order, deduping exact repeats.
    """
    objs: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def _push(obj: Dict[str, Any]):
        if not isinstance(obj, dict) or "tool" not in obj:
            return
        sig = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        if sig not in seen:
            seen.add(sig)
            objs.append(obj)

    s = _strip_code_fences((mixed or "").strip())
    if not s:
        return objs

    # 1) Try whole-string JSON
    try:
        data = json.loads(s)
        if isinstance(data, dict) and "tool" in data:
            _push(data)
            return objs
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "tool" in item:
                    _push(item)
            if objs:
                return objs
    except Exception:
        pass

    # 2) JSONL path
    for line in s.splitlines():
        ln = line.strip()
        if not ln or not ln.startswith("{") or '"tool"' not in ln:
            continue
        try:
            data = json.loads(ln)
            if isinstance(data, dict) and "tool" in data:
                _push(data)
        except Exception:
            continue

    if objs:
        return objs

    # 3) Fallback: scan object/array spans and parse those
    for m in re.finditer(r"\{.*?\}|\[.*?\]", s, flags=re.DOTALL):
        cand = m.group(0)
        if '"tool"' not in cand:
            continue
        try:
            data = json.loads(cand)
            if isinstance(data, dict) and "tool" in data:
                _push(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "tool" in item:
                        _push(item)
        except Exception:
            continue

    return objs

# -------------------------------------------------------------------
# Safe context & helper formatters (no ORM leakage)
# -------------------------------------------------------------------
def _safe_docs_summary(bundle: Dict[str, Any]) -> str:
    try:
        return _summarize_docs(bundle.get("docs", []))
    except TypeError:
        return _summarize_docs(bundle)

def _safe_decision_overview(bundle: Dict[str, Any]) -> str:
    decision = bundle.get("decision")
    try:
        return _explain_decision(decision)
    except TypeError:
        return _explain_decision(bundle)

def _make_context(bundle: Dict[str, Any]) -> str:
    app = bundle.get("app")
    docs_summary = _safe_docs_summary(bundle)
    decision_overview = _safe_decision_overview(bundle)

    full_name = getattr(app, "full_name", None) or "N/A"
    age = getattr(app, "age", None)
    income = getattr(app, "net_monthly_income", None)
    oblig = getattr(app, "credit_obligations_ratio", None)
    address = getattr(app, "address", None) or "N/A"

    lines = [
        f"Applicant: {full_name}, age: {age if age is not None else 'N/A'}",
        f"Address: {address}",
        f"Income: {income if income is not None else 'N/A'}, Obligations ratio: {oblig if oblig is not None else 'N/A'}",
        "",
        "Documents (summary):",
        docs_summary if docs_summary else "No documents.",
        "",
        "Latest decision:",
        decision_overview if decision_overview else "No decision yet.",
    ]
    return "\n".join(lines)

# -------------------------------------------------------------------
# Public entry: called by main.py as react_chat(db, application_id, user_message)
# -------------------------------------------------------------------
def react_chat(db: Session, application_id: str, user_message: str) -> str:
    """
    ReAct-lite:
      1) Build context, call Ollama with system+user.
      2) If the model emits one or more tool calls, execute them deterministically.
      3) Compose a clean, human-readable answer (no raw JSON).
      4) If no tool calls, return the model’s direct answer.
    """
    # 1) Load bundle
    bundle = _load_application_bundle(db, application_id)
    if isinstance(bundle, dict) and "error" in bundle:
        return bundle["error"]

    # 2) Prepare context for the model
    context = _make_context(bundle)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nUSER: {user_message}"},
    ]

    # 3) Call LLM exactly once
    try:
        first = _ollama_chat(messages)
    except Exception as ex:
        return f"LLM error: {ex}"

    # 4) Parse tool calls (supports JSON/JSONL/arrays/fenced)
    calls = _extract_tool_json_objects(first)

    # Tool alias map (lower-cased)
    DOCS_ALIASES = {"docs_summary", "summarize_documents"}
    DECISION_ALIASES = {"decision_overview", "explain_decision"}

    # 5) Execute tools in order and format
    if calls:
        parts: List[str] = []
        seen = set()
        for call in calls:
            tool = (call.get("tool") or "").strip().lower()
            # de-dupe identical consecutive tools by signature
            sig = json.dumps(call, sort_keys=True, ensure_ascii=False)
            if sig in seen:
                continue
            seen.add(sig)

            if tool in DOCS_ALIASES:
                parts.append("**Documents Summary**\n" + _safe_docs_summary(bundle))

            elif tool in DECISION_ALIASES:
                parts.append("**Decision Explanation**\n" + _safe_decision_overview(bundle))

            else:
                # ignore unknown tools deterministically
                continue

        if parts:
            return "\n\n".join(parts)

    # 6) No tool usage; return the direct model reply
    return first
