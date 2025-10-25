from __future__ import annotations
from io import BytesIO
from typing import Tuple, Optional
import pdfplumber

def _make_preview(text: str, max_len: int = 380) -> str:
    text = " ".join(text.split())
    return text[:max_len]

def extract_text_from_pdf(raw: bytes) -> Tuple[str, str]:
    """Return (full_text, preview)."""
    out = []
    with pdfplumber.open(BytesIO(raw)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t:
                out.append(t)
    all_text = "\n".join(out).strip()
    return all_text, _make_preview(all_text)

def extract_text_generic(raw: bytes, content_type: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    For now:
      - PDFs → full text via pdfplumber
      - Others → no OCR (return None)
    """
    if content_type and "pdf" in content_type.lower():
        try:
            return extract_text_from_pdf(raw)
        except Exception:
            return "", ""
    return None, None
