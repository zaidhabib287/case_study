from __future__ import annotations
from functools import lru_cache
from typing import Dict, Any
from sqlalchemy.orm import Session
from ..app.models import Application, Document
import joblib
import os

MODEL_PATH = os.getenv("ELIGIBILITY_MODEL_PATH", "/app/models/baseline.joblib")

@lru_cache
def _load_pipeline():
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None

def _features_for_app(db: Session, application_id: str) -> Dict[str, float]:
    """Turn an Application + its docs into a flat feature dict."""
    app = db.query(Application).filter_by(application_id=application_id).first()
    docs = db.query(Document).filter_by(application_id=application_id).all()
    doc_count = len(docs)
    avg_text_len = 0.0
    if doc_count:
        lengths = [(len(d.content_text) if d.content_text else 0) for d in docs]
        avg_text_len = sum(lengths) / doc_count if lengths else 0.0

    return {
        "age": float(app.age or 0),
        "income": float(app.net_monthly_income or 0),
        "obligations_ratio": float(app.credit_obligations_ratio if app.credit_obligations_ratio is not None else 0.0),
        "dependents": float(app.dependents_under_12 or 0),
        "doc_count": float(doc_count),
        "avg_text_len": float(avg_text_len),
    }

def predict_probability(db: Session, application_id: str) -> float | None:
    pipe = _load_pipeline()
    if pipe is None:
        return None
    feats = _features_for_app(db, application_id)
    # keep input order consistent with training script
    X = [[
        feats["age"],
        feats["income"],
        feats["obligations_ratio"],
        feats["dependents"],
        feats["doc_count"],
        feats["avg_text_len"],
    ]]
    try:
        proba = pipe.predict_proba(X)[0][1]
        return float(proba)
    except Exception:
        return None
