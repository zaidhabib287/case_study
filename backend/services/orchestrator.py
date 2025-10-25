from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from typing import Dict, Any

from .agent_react import react_chat

# Keep DB session out of state (store here)
_DB = None  # type: ignore

def set_db_session(db):
    global _DB
    _DB = db

# Simple state container
class State(dict):
    pass

def _unwrap(state: State) -> Dict[str, Any]:
    """
    Accept both:
      {"application_id": "...", "user_message":"..."}
    and:
      {"input": {"application_id":"...", "user_message":"..."}}
    """
    if "application_id" in state and "user_message" in state:
        return state
    if "input" in state and isinstance(state["input"], dict):
        return state["input"]
    return state  # best effort

def classify_node(state: State) -> State:
    # trivial pass-through; you could route to different tools here
    return state

def act_node(state: State) -> State:
    if _DB is None:
        state["reply"] = "Internal error: DB not available."
        return state

    data = _unwrap(state)
    app_id = data.get("application_id")
    user_msg = data.get("user_message")

    if not app_id or not user_msg:
        state["reply"] = "Internal error: missing application_id or user_message."
        return state

    reply = react_chat(_DB, app_id, user_msg)
    state["reply"] = reply
    return state

def build_graph():
    g = StateGraph(State)
    g.add_node("classify", classify_node)
    g.add_node("act", act_node)
    g.add_edge(START, "classify")
    g.add_edge("classify", "act")
    g.add_edge("act", END)
    return g.compile()
