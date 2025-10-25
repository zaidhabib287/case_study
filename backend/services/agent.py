from __future__ import annotations
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# Adjust import path to your actual models module
from ..app.models import Application, Document, Decision

def _load_application_bundle(db: Session, application_id: str) -> Dict[str, Any]:
    app: Optional[Application] = db.get(Application, application_id)
    if not app:
        return {"error": f"Application {application_id} not found"}
    docs: List[Document] = db.query(Document).filter_by(application_id=application_id).all()
    last_decision: Optional[Decision] = (
        db.query(Decision).filter_by(application_id=application_id)
        .order_by(Decision.created_at.desc())
        .first()
    )
    return {"app": app, "docs": docs, "decision": last_decision}

def _make_preview(text: str, max_len: int = 160) -> str:
    return " ".join((text or "").split())[:max_len]

def _summarize_docs(docs: List[Document], limit: int = 3) -> str:
    if not docs:
        return "No documents available."
    lines = []
    for d in docs[:limit]:
        preview = (d.content_preview or "")
        lines.append(
            f"- {d.filename} ({d.content_type or 'unknown'}, {d.size_bytes or 0} bytes) :: {_make_preview(preview)}"
        )
    more = "" if len(docs) <= limit else f"\n(+{len(docs)-limit} more)"
    return "\n".join(lines) + more

def _explain_decision(decision: Optional[Decision]) -> str:
    if not decision:
        return "No decision has been run yet. Use the Run step first."
    base = f"Latest decision: **{decision.status}** (label: {decision.eligibility_label}, p={round(decision.probability or 0.0, 3)}).\n"
    why  = f"Rationale: {decision.rationale or 'N/A'}"
    return base + why

def _format_validation_note(decision: Optional[Decision]) -> str:
    if not decision:
        return "No decision exists yet; run the pipeline to populate validation checks."
    return (
        "- Validation checks were evaluated during the last run.\n"
        "- See UI 'Decision' panel for pass/warn/fail bullets."
    )

def _format_recommendations(decision: Optional[Decision]) -> str:
    if not decision:
        return "No decision exists yet; run the pipeline to generate tailored recommendations."
    if decision.eligibility_label in ("approve", "review"):
        return (
            "- Proceed to onboarding.\n"
            "- If underwriting requests a document, upload it in the Upload tab.\n"
            "- Keep income proof and bank statement handy for faster closure."
        )
    return (
        "- Address validation blockers (missing docs or policy constraints).\n"
        "- Re-upload clearer PDFs (full page, legible text).\n"
        "- Re-run after fixes."
    )

def chat_answer(db: Session, application_id: str, messages: List[Dict[str, str]]) -> str:
    """
    Simple rules-based agent (no LLM). Supports:
    - overview
    - documents summary
    - decision explanation
    - recommendations
    """
    bundle = _load_application_bundle(db, application_id)
    if "error" in bundle:
        return bundle["error"]

    app: Application = bundle["app"]
    docs: List[Document] = bundle["docs"]
    decision: Optional[Decision] = bundle["decision"]

    # find last user message
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").lower()
            break

    if any(k in last_user for k in ["doc", "document", "pdf", "upload", "summary", "summarize"]):
        return f"**Documents (top 3):**\n{_summarize_docs(docs)}"

    if any(k in last_user for k in ["validat", "check", "pass", "warn", "fail"]):
        return _format_validation_note(decision)

    if any(k in last_user for k in ["eligib", "approve", "score", "probab", "decision"]):
        return _explain_decision(decision)

    if any(k in last_user for k in ["next step", "recommend", "what next"]):
        return _format_recommendations(decision)

    if any(k in last_user for k in ["status", "overview", "what happened"]):
        parts = [
            f"Applicant: **{app.full_name or 'N/A'}** (age {app.age or 'N/A'})",
            f"Income: {app.net_monthly_income or 'N/A'} | Obligations ratio: "
            f"{app.credit_obligations_ratio if app.credit_obligations_ratio is not None else 'N/A'}",
            f"Docs: {len(docs)} uploaded",
            _explain_decision(decision),
        ]
        return "\n".join(parts)

    # default help
    return (
        "I can help with:\n"
        "- Overview of the application\n"
        "- Documents summary\n"
        "- Validation explanation\n"
        "- Eligibility (decision & probability)\n"
        "- Recommendations / next steps\n"
        "Try asking: “summarize my documents”, “why soft-decline?”, or “what’s my score?”"
    )
