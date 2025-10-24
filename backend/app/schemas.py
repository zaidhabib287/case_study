from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr, validator, conint, confloat
from typing import List, Optional, Literal
from enum import Enum

# ---------- Enums ----------
class EmploymentStatus(str, Enum):
    employed = "employed"
    self_employed = "self_employed"
    unemployed = "unemployed"
    student = "student"
    retired = "retired"

class DocumentType(str, Enum):
    bank_statement = "bank_statement"
    emirates_id = "emirates_id"
    credit_report = "credit_report"
    payslip = "payslip"
    other = "other"

# ---------- DTOs: inbound ----------
class HouseholdMember(BaseModel):
    name: str = Field(..., min_length=1)
    age: conint(ge=0, le=120)  # type: ignore
    relation: str = Field(..., min_length=2)

class ContactInfo(BaseModel):
    email: Optional[EmailStr] = None
    phone_e164: Optional[str] = Field(None, description="E.164 format, e.g. +9715xxxxxxx")

class ApplicationIn(BaseModel):
    application_id: str = Field(..., description="Client-supplied unique application id")
    full_name: str = Field(..., min_length=3)
    age: conint(ge=18, le=100)  # type: ignore
    address: str = Field(..., min_length=3)
    region_code: Optional[str] = Field(None, description="e.g. DXB, AUH, etc.")
    employment_status: EmploymentStatus = EmploymentStatus.employed
    net_monthly_income: Optional[confloat(ge=0)] = None  # type: ignore
    credit_obligations_ratio: Optional[confloat(ge=0, le=1)] = None  # type: ignore
    dependents_under_12: Optional[conint(ge=0, le=20)] = 0  # type: ignore
    household: List[HouseholdMember] = []
    contact: Optional[ContactInfo] = None

    @validator("credit_obligations_ratio")
    def _ratio_hint(cls, v):
        # If supplied, give a friendly bound reminder (already enforced by type)
        return v

# ---------- DTOs: documents ----------
class DocumentMeta(BaseModel):
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    doc_type: Optional[DocumentType] = DocumentType.other
    ocr_confidence: Optional[confloat(ge=0, le=1)] = None  # type: ignore

class UploadResponse(BaseModel):
    uploaded: List[DocumentMeta]

# ---------- DTOs: validation / eligibility / decision ----------
class ValidationResult(BaseModel):
    pass_checks: List[str] = []
    warn_checks: List[str] = []
    fail_checks: List[str] = []

class EligibilityResult(BaseModel):
    label: Literal["approve", "soft_decline", "manual_review"]
    probability: confloat(ge=0, le=1)  # type: ignore
    reasons: List[str]

class Recommendation(BaseModel):
    text: str

class DecisionOut(BaseModel):
    application_id: str
    status: Literal["Approve", "Soft-Decline", "Manual-Review"]
    validation: ValidationResult
    eligibility: EligibilityResult
    recommendations: List[str]
    rationale: str

# ---------- Error envelope ----------
class ApiError(BaseModel):
    error: str
    details: Optional[dict] = None
