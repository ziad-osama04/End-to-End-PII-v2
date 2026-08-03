"""Unit tests for pdf_masking.py.

Uses the dependency-free regex Masker's detect_spans as the DetectFn -- no
MedRoBERTa/torch needed, since pdf_masking.py only depends on that callable's
signature, not on which masker produced it.
"""
from __future__ import annotations

import shutil

import pytest

fitz = pytest.importorskip("fitz")

from masking_service import masking_core as core  # noqa: E402
from masking_service import pdf_masking  # noqa: E402

DETECT = core.Masker().detect_spans

PII = {
    "email": "jan.jansen@example.com",
    "phone": "0475123456",
    "iban": "BE68539007547034",
}


def _text_pdf(lines: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    for i, line in enumerate(lines):
        page.insert_text((72, 72 + i * 24), line, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def _pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    doc.close()
    return text


# --------------------------------------------------------------------------- #
# pdf_supported
# --------------------------------------------------------------------------- #
def test_pdf_supported_true_when_fitz_installed():
    assert pdf_masking.pdf_supported() is True


# --------------------------------------------------------------------------- #
# mask_pdf -- success paths
# --------------------------------------------------------------------------- #
def test_mask_pdf_removes_pii_and_adds_placeholder():
    pdf = _text_pdf([f"Patient email {PII['email']}", f"Telefoon {PII['phone']}"])
    out, count = pdf_masking.mask_pdf(pdf, DETECT)
    assert count >= 2
    text = _pdf_text(out)
    assert PII["email"] not in text
    assert PII["phone"] not in text
    assert "<EMAIL>" in text and "<PHONE>" in text


def test_mask_pdf_output_is_a_valid_pdf():
    pdf = _text_pdf([f"mail {PII['email']}"])
    out, _ = pdf_masking.mask_pdf(pdf, DETECT)
    doc = fitz.open(stream=out, filetype="pdf")
    try:
        assert doc.page_count == 1
    finally:
        doc.close()


def test_mask_pdf_preserves_page_count_and_dimensions():
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 72), "MEDISCH RAPPORT")
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((72, 72), f"IBAN {PII['iban']}")
    in_pages = doc.page_count
    in_dims = [(round(p.rect.width), round(p.rect.height)) for p in doc]
    pdf_in = doc.tobytes()
    doc.close()

    out, _ = pdf_masking.mask_pdf(pdf_in, DETECT)
    check = fitz.open(stream=out, filetype="pdf")
    try:
        assert check.page_count == in_pages
        assert [(round(p.rect.width), round(p.rect.height)) for p in check] == in_dims
    finally:
        check.close()


def test_mask_pdf_no_pii_leaves_text_intact():
    pdf = _text_pdf(["Gewoon een rapport zonder identificerende gegevens."])
    out, count = pdf_masking.mask_pdf(pdf, DETECT)
    assert count == 0
    assert "Gewoon een rapport" in _pdf_text(out)


def test_mask_pdf_is_deterministic():
    pdf = _text_pdf([f"mail {PII['email']}", f"iban {PII['iban']}"])
    out1, _ = pdf_masking.mask_pdf(pdf, DETECT)
    out2, _ = pdf_masking.mask_pdf(pdf, DETECT)
    assert out1 == out2


# --------------------------------------------------------------------------- #
# mask_pdf -- failure paths (contract v1.2: fail closed, never leak input)
# --------------------------------------------------------------------------- #
def test_mask_pdf_corrupt_bytes_raises():
    with pytest.raises(core.MaskingError):
        pdf_masking.mask_pdf(b"not a pdf at all", DETECT)


def test_mask_pdf_password_protected_raises():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret")
    encrypted = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret"
    )
    doc.close()
    with pytest.raises(core.MaskingError):
        pdf_masking.mask_pdf(encrypted, DETECT)


def test_mask_pdf_failure_never_leaks_original_bytes():
    corrupt = b"%PDF-1.4 " + PII["email"].encode() + b" broken"
    with pytest.raises(core.MaskingError) as exc_info:
        pdf_masking.mask_pdf(corrupt, DETECT)
    assert PII["email"] not in str(exc_info.value)


# --------------------------------------------------------------------------- #
# _locate -- token-fallback search, tested directly against a stub page.
# --------------------------------------------------------------------------- #
class _StubPage:
    """Minimal stand-in for a fitz.Page, controlling search_for's return value."""

    def __init__(self, hits: dict[str, list]):
        self._hits = hits

    def search_for(self, needle):
        return self._hits.get(needle, [])


def test_locate_returns_direct_hit_when_whole_value_found():
    page = _StubPage({"jan.jansen@example.com": ["rect1"]})
    assert pdf_masking._locate(page, "jan.jansen@example.com") == ["rect1"]


def test_locate_falls_back_to_tokens_when_whole_value_not_found():
    # e.g. a value split across a line break: search_for(full) fails, but each
    # whitespace-separated token is found individually.
    page = _StubPage({"Jan": ["rect_jan"], "Peeters": ["rect_peeters"]})
    assert pdf_masking._locate(page, "Jan Peeters") == ["rect_jan", "rect_peeters"]


def test_locate_returns_empty_when_nothing_found():
    page = _StubPage({})
    assert pdf_masking._locate(page, "nowhere to be found") == []


def test_locate_does_not_fall_back_for_single_token_value():
    # A single unmatched token should not spuriously combine partial matches.
    page = _StubPage({})
    assert pdf_masking._locate(page, "onlyoneword") == []


# --------------------------------------------------------------------------- #
# Scanned-page OCR path -- needs the actual tesseract binary, not just the
# pytesseract package, so it's skipped when that's unavailable.
# --------------------------------------------------------------------------- #
requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract binary not installed"
)


@pytest.mark.slow
@requires_tesseract
def test_mask_pdf_scanned_page_ocr_masks_pii():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"contact {PII['email']}", fontsize=14)
    pix = page.get_pixmap(dpi=200)

    scanned = fitz.open()
    scan_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
    scan_page.insert_image(scan_page.rect, pixmap=pix)
    scanned_bytes = scanned.tobytes()
    doc.close()
    scanned.close()

    out, count = pdf_masking.mask_pdf(scanned_bytes, DETECT)
    assert count >= 1
    check = fitz.open(stream=out, filetype="pdf")
    check.close()
