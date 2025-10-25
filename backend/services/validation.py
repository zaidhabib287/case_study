from __future__ import annotations
from typing import List, Tuple
from sqlalchemy.orm import Session
from ..app.models import Application, Document
from ..app.schemas import ValidationResult

def _has_keyword(doc: Document, *keywords: str) -> bool:
    text = (doc.content_text or "").lower()
    return any(k.lower() in text for k in keywords)

def _required_docs_exist(docs: List[Document]) -> Tuple[bool, List[str]]:
    reasons = []
    ok = True

    if not docs:
        ok = False
        reasons.append("No documents uploaded.")
        return ok, reasons

    # Example doc checks (customize later):
    has_bank_stmt = any(_has_keyword(d, "statement", "bank") for d in docs)
    has_income_proof = any(_has_keyword(d, "salary", "payslip", "income") for d in docs)

    if not has_bank_stmt:
        ok = False
        reasons.append("Missing or unreadable bank statement.")
    if not has_income_proof:
        ok = False
        reasons.append("Missing or unreadable income proof (salary/payslip).")

    return ok, reasons

def validate_application(db: Session, application_id: str) -> ValidationResult:
    app = db.get(Application, application_id)
    docs: List[Document] = db.query(Document).filter_by(application_id=application_id).all()

    pass_checks: List[str] = []
    warn_checks: List[str] = []
    fail_checks: List[str] = []

    # Basic field checks
    if app.full_name and len(app.full_name) >= 3:
        pass_checks.append("full_name_present")
    else:
        fail_checks.append("full_name_missing")

    if app.age is not None and 18 <= app.age <= 100:
        pass_checks.append("age_valid")
    else:
        fail_checks.append("age_invalid")

    if app.address and len(app.address) >= 3:
        pass_checks.append("address_present")
    else:
        fail_checks.append("address_missing")

    # Income checks (example policy, tweak as needed)
    if app.net_monthly_income is None:
        warn_checks.append("income_missing")
    elif app.net_monthly_income < 2500:
        fail_checks.append("income_below_min_threshold")
    else:
        pass_checks.append("income_meets_min_threshold")

    # Debt ratio check (optional; only if provided)
    if app.credit_obligations_ratio is not None:
        if 0 <= app.credit_obligations_ratio <= 1:
            pass_checks.append("obligations_ratio_in_range")
        else:
            fail_checks.append("obligations_ratio_out_of_range")

    # Document checks using parsed text
    docs_ok, doc_reasons = _required_docs_exist(docs)
    if docs_ok:
        pass_checks.append("required_documents_present")
    else:
        fail_checks.extend([f"doc_check: {r}" for r in doc_reasons])

    return ValidationResult(
        pass_checks=pass_checks,
        warn_checks=warn_checks,
        fail_checks=fail_checks
    )
