# ingestion/pdf_ocr.py
from __future__ import annotations
from io import BytesIO
from typing import Dict, Tuple


def _plumber_extract(pdf_bytes: bytes) -> Tuple[str, Dict]:
    import pdfplumber
    text_chunks = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        meta = {"ocr_used": False, "pages": len(pdf.pages)}
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            text_chunks.append(t)
    text = "\n".join(text_chunks).strip()
    return text, meta


def _ocr_fallback(pdf_bytes: bytes) -> Tuple[str, Dict]:
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes)
        parts = []
        for img in images:
            parts.append(pytesseract.image_to_string(img))
        text = "\n".join(parts).strip()
        return text, {"ocr_used": True, "pages": len(images)}
    except Exception:
        return "", {"ocr_used": True, "pages": 0}


def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, Dict]:
    """Try pdfplumber first; if very short, OCR as fallback."""
    text, meta = _plumber_extract(pdf_bytes)
    if len(text) < 50:  # heuristic: likely scanned/no text layer
        ocr_text, ocr_meta = _ocr_fallback(pdf_bytes)
        if len(ocr_text) > len(text):
            return ocr_text, ocr_meta
    return text, meta