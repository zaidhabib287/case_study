from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from .schemas import (
    ApplicationIn, DecisionOut, ValidationResult, EligibilityResult,
    UploadResponse, DocumentMeta, ApiError
)

app = FastAPI(title="Case Study API", version="1.0.0")
DB = {}  # demo in-memory store

@app.get("/health")
async def health():
    return {"ok": True, "service": "api", "version": "1.0.0"}

@app.post("/applications", responses={400: {"model": ApiError}})
async def create_application(app_in: ApplicationIn):
    if app_in.application_id in DB:
        raise HTTPException(status_code=400, detail=f"application_id {app_in.application_id} already exists")
    DB[app_in.application_id] = {"data": app_in.dict(), "status": "created", "docs": []}
    return {"ok": True, "application_id": app_in.application_id}

@app.post(
    "/applications/{application_id}/upload",
    response_model=UploadResponse,
    responses={404: {"model": ApiError}}
)
async def upload_documents(application_id: str, files: List[UploadFile] = File(...)):
    if application_id not in DB:
        raise HTTPException(status_code=404, detail=f"application {application_id} not found")

    metas: List[DocumentMeta] = []
    DB.setdefault(application_id, {}).setdefault("docs", [])

    for f in files:
        content = await f.read()
        meta = DocumentMeta(filename=f.filename, content_type=f.content_type, size_bytes=len(content))
        DB[application_id]["docs"].append(meta.dict())
        metas.append(meta)

    return UploadResponse(uploaded=metas)

@app.post(
    "/applications/{application_id}/run",
    response_model=DecisionOut,
    responses={404: {"model": ApiError}}
)
async def run_pipeline(application_id: str):
    if application_id not in DB:
        raise HTTPException(status_code=404, detail=f"application {application_id} not found")

    # TODO (Phase 3+): call parsers, validations, model, and RAG
    validation = ValidationResult(pass_checks=["address_present"], warn_checks=[], fail_checks=[])
    eligibility = EligibilityResult(label="approve", probability=0.82, reasons=["Income within threshold", "Low obligations"])
    recommendations = ["Enroll in 'Retail CRM Basics'", "Attend budgeting workshop"]

    DB[application_id]["status"] = "completed"
    return DecisionOut(
        application_id=application_id,
        status="Approve",
        validation=validation,
        eligibility=eligibility,
        recommendations=recommendations,
        rationale="Meets policy criteria; see reasons.",
    )

# ---- Global error handler for uniform envelope (optional nice-to-have) ----
@app.exception_handler(HTTPException)
async def http_exc_handler(_, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=ApiError(error=str(exc.detail)).dict())
