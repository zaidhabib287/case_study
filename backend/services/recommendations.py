from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from ..app.models import Application, Document
from ..app.schemas import ValidationResult, EligibilityResult

def _has_doc(docs: List[Document], *keywords: str) -> bool:
    for d in docs:
        text = (d.content_text or "").lower()
        if any(k.lower() in text for k in keywords):
            return True
    return False

def recommend(
    db: Session,
    application_id: str,
    validation: ValidationResult,
    eligibility: EligibilityResult,
) -> List[str]:
    app = db.query(Application).filter_by(application_id=application_id).first()
    docs = db.query(Document).filter_by(application_id=application_id).all()

    recs: List[str] = []

    # 1) Hard blockers from validation
    if validation.fail_checks:
        if any("bank statement" in r for r in validation.fail_checks):
            recs.append("Upload a recent bank statement (last 3 months).")
        if any("income proof" in r for r in validation.fail_checks):
            recs.append("Upload income proof (salary slip / employment letter).")
        if "income_below_min_threshold" in validation.fail_checks:
            recs.append("Consider adding a co-applicant or increasing declared income.")
        if "age_invalid" in validation.fail_checks:
            recs.append("Not eligible due to age policy; reapply when policy criteria are met.")
        # If any blockers, these two generic actions help:
        recs.append("Ensure documents are clear, full-page scans (avoid photos/crops).")
        recs.append("Re-submit after fixing the above validation issues.")
        return recs

    # 2) Soft nudges from warnings (if you add warnings later)
    if validation.warn_checks:
        recs.append("Some checks raised warnings — verify all details before final submit.")

    # 3) Document quality nudges
    if not _has_doc(docs, "statement", "bank"):
        recs.append("Optionally attach a bank statement to speed up manual review.")
    if not _has_doc(docs, "salary", "payslip", "income"):
        recs.append("Optionally attach a payslip/income proof to strengthen the application.")

    # 4) Feature-based support
    if (app.credit_obligations_ratio or 0) > 0.5:
        recs.append("Consider debt consolidation or lowering existing obligations.")
    if (app.net_monthly_income or 0) < 3000:
        recs.append("Explore budgeting resources and income-boost programs.")

    # 5) Outcome-based recommendations
    p = eligibility.probability or 0.0
    if eligibility.label == "approve":
        if p >= 0.75:
            recs.append("Fast-track onboarding — all signals look strong.")
        else:
            recs.append("Proceed to onboarding; underwriting may request one more document.")
    elif eligibility.label == "review":
        recs.append("Manual review recommended — add any missing docs to accelerate.")
    else:
        # fallback; shouldn’t hit if fail_checks handled above
        recs.append("Follow up with support for the next steps.")

    # Always end with at least one actionable step
    if not recs:
        recs.append("Proceed to next onboarding step.")

    return recs
