from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .db import get_db
from .models import Application, Document, Decision
from .schemas import (
    ApplicationIn,
    DecisionOut,
    ValidationResult,
    EligibilityResult,
    UploadResponse,
    DocumentMeta,
    ApiError,
)
from .security import require_api_key
from .logging_setup import setup_logging
from .middleware import RequestIDMiddleware

from ..services.parsing import extract_text_generic
from ..services.validation import validate_application
from ..services.ml import predict_probability
from ..services.recommendations import recommend
from ..services.agent import chat_answer          # rules engine (no LLM)
from ..services.agent_react import react_chat     # ReAct + Ollama (direct)
from ..services.orchestrator import build_graph, set_db_session  # LangGraph wrapper

# ---- app bootstrap ----
setup_logging()
app = FastAPI(title="Case Study API", version="2.0.0")
app.add_middleware(RequestIDMiddleware)

# ---- health ----
@app.get("/health")
async def health():
    return {"ok": True, "service": "api", "version": "2.0.0"}

# ---- create application ----
@app.post(
    "/applications",
    responses={400: {"model": ApiError}},
    dependencies=[Depends(require_api_key)],
)
async def create_application(app_in: ApplicationIn, db: Session = Depends(get_db)):
    # uniqueness check
    exists = db.get(Application, app_in.application_id)
    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"application_id {app_in.application_id} already exists",
        )

    # persist
    app_row = Application(
        application_id=app_in.application_id,
        full_name=app_in.full_name,
        age=app_in.age,
        address=app_in.address,
        region_code=app_in.region_code,
        employment_status=(
            app_in.employment_status.value
            if hasattr(app_in.employment_status, "value")
            else str(app_in.employment_status)
        ),
        net_monthly_income=app_in.net_monthly_income,
        credit_obligations_ratio=app_in.credit_obligations_ratio,
        dependents_under_12=app_in.dependents_under_12,
    )
    db.add(app_row)
    db.commit()
    return {"ok": True, "application_id": app_in.application_id}

# ---- upload docs ----
@app.post(
    "/applications/{application_id}/upload",
    response_model=UploadResponse,
    responses={404: {"model": ApiError}},
    dependencies=[Depends(require_api_key)],
)
async def upload_documents(
    application_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    app_row = db.get(Application, application_id)
    if not app_row:
        raise HTTPException(status_code=404, detail=f"application {application_id} not found")

    metas: List[DocumentMeta] = []
    for f in files:
        content = await f.read()
        full_text, preview = extract_text_generic(content, f.content_type)
        meta = DocumentMeta(
            filename=f.filename,
            content_type=f.content_type,
            size_bytes=len(content),
        )
        db.add(
            Document(
                application_id=application_id,
                filename=meta.filename,
                content_type=meta.content_type,
                size_bytes=meta.size_bytes,
                content_text=full_text,
                content_preview=preview,
            )
        )
        metas.append(meta)
    db.commit()
    return UploadResponse(uploaded=metas)

# ---- run decision pipeline ----
@app.post(
    "/applications/{application_id}/run",
    response_model=DecisionOut,
    responses={404: {"model": ApiError}},
    dependencies=[Depends(require_api_key)],
)
async def run_pipeline(application_id: str, db: Session = Depends(get_db)):
    app_row = db.get(Application, application_id)
    if not app_row:
        raise HTTPException(status_code=404, detail=f"application {application_id} not found")

    # 1) validation
    validation: ValidationResult = validate_application(db, application_id)

    # 2) decision via validation + model
    if validation.fail_checks:
        status = "Soft-Decline"
        eligibility = EligibilityResult(
            label="soft_decline",
            probability=0.35,
            reasons=["Validation failed"],
        )
    else:
        proba = predict_probability(db, application_id)
        if proba is None:
            proba = 0.7  # fallback heuristic
        label = "approve" if proba >= 0.5 else "review"
        status = "Approve" if label == "approve" else "Manual-Review"
        eligibility = EligibilityResult(
            label=label,
            probability=round(float(proba), 3),
            reasons=["Baseline ML scorer"],
        )

    rationale = "Validation + baseline ML scorer."

    db.add(
        Decision(
            application_id=application_id,
            status=status,
            eligibility_label=eligibility.label,
            probability=eligibility.probability,
            rationale=rationale,
        )
    )
    db.commit()

    recs = recommend(db, application_id, validation, eligibility)

    return DecisionOut(
        application_id=application_id,
        status=status,
        validation=validation,
        eligibility=eligibility,
        recommendations=recs,
        rationale=rationale,
    )

# ---- chat schemas ----
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    application_id: str
    messages: List[ChatMessage]
    use_llm: bool = True  # toggle from UI

# ---- chat endpoint ----
@app.post("/chat", dependencies=[Depends(require_api_key)])
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        # last user message
        user_msg = ""
        for m in reversed(req.messages):
            if m.role == "user":
                user_msg = m.content
                break

        # Fallback to local rules-based agent (no LLM)
        if not req.use_llm or os.getenv("USE_OLLAMA", "1") != "1":
            text = chat_answer(db, req.application_id, [mm.model_dump() for mm in req.messages])
            return {"ok": True, "reply": text}

        # ---- LangGraph orchestration (robust + fallback) ----
        try:
            set_db_session(db)
            graph = build_graph()
            out = graph.invoke(
                {"application_id": req.application_id, "user_message": user_msg}
            )
            return {"ok": True, "reply": out.get("reply", "No reply.")}
        except Exception as lg_err:
            # Fallback: direct ReAct + Ollama if graph hiccups
            reply = react_chat(db, req.application_id, user_msg)
            return {"ok": True, "reply": reply}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---- error handling ----
@app.exception_handler(HTTPException)
async def http_exc_handler(_, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiError(error=str(exc.detail)).dict(),
    )
