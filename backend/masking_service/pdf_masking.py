"""Mask PII in PDF files, returning a valid masked PDF (contract v1.2).

Two paths, chosen per page:

* **Text PDFs** — extract the page text, run the masker's ``detect_spans`` over
  it, locate each detected value with ``page.search_for``, and remove it with a
  PyMuPDF redaction annotation (``add_redact_annot`` + ``apply_redactions``).
  This deletes the original glyphs from the content stream, not just paints over
  them, and draws the ``<LABEL>`` placeholder in their place.

* **Scanned pages** (an image with no extractable text) — OCR the rendered page
  with pytesseract to recover text and per-word boxes, detect PII in that text,
  and redact the pixels under each PII word. Reuses the same extraction stack as
  the demo redaction API (``backend/src/ingestion/router.py``).

The heavy libraries (PyMuPDF, pytesseract, Pillow) are imported lazily so the
dependency-free ``masking_core`` and the light API image stay importable without
them. ``pdf_supported()`` lets the service advertise ``application/pdf`` on
``/version`` only when it can genuinely process it.

Failure policy (contract v1.2 sections 3 and 5): a password-protected, corrupt,
or otherwise unreadable PDF, and any detected PII that cannot be mapped to page
geometry, raise :class:`masking_core.MaskingError` -> HTTP 422. The service
never returns a PDF it could not fully mask.
"""
from __future__ import annotations

import importlib.util
import io
import re
from typing import Callable, List, Tuple

from masking_service import masking_core as core

# A function that returns (start, end, label) PII spans for a text string. Both
# the regex-poc-1 base Masker and the MedRoBERTa masker implement this.
DetectFn = Callable[[str], List[Tuple[int, int, str]]]

# Render scanned pages at this resolution before OCR. Higher is more accurate
# and slower; 200 DPI is a good balance for A4 clinical documents.
_OCR_DPI = 200
_OCR_LANG = "nld"


def pdf_supported() -> bool:
    """Return whether PyMuPDF is importable, i.e. PDF masking can run."""
    return importlib.util.find_spec("fitz") is not None


def _ocr_available() -> bool:
    """Return whether the OCR stack (pytesseract + Pillow) is importable."""
    return (
        importlib.util.find_spec("pytesseract") is not None
        and importlib.util.find_spec("PIL") is not None
    )


def mask_pdf(raw: bytes, detect_spans: DetectFn) -> Tuple[bytes, int]:
    """Return ``(masked_pdf_bytes, entity_count)`` for a PDF input.

    Raises :class:`masking_core.MaskingError` on any unreadable input or any
    detected PII that cannot be located on the page.
    """
    import fitz  # PyMuPDF; imported lazily

    try:
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - any parse failure is a 422
        raise core.MaskingError("invalid or unsupported PDF") from exc

    total = 0
    try:
        if doc.needs_pass:
            raise core.MaskingError("password-protected PDF")
        if doc.page_count == 0:
            raise core.MaskingError("empty PDF")

        for page in doc:
            total += _mask_page(fitz, page, detect_spans)

        buf = io.BytesIO()
        # Deterministic bytes for a given input and deployment: garbage-collect
        # and deflate, and keep the source trailer id (a fresh id is random).
        # NiFi replays a request with the same idempotency key, so identical
        # input must produce identical output.
        doc.save(buf, deflate=True, garbage=4, no_new_id=True)
        out = buf.getvalue()
    finally:
        doc.close()

    # Validate the result opens as a PDF before returning it.
    try:
        check = fitz.open(stream=out, filetype="pdf")
        check.close()
    except Exception as exc:  # noqa: BLE001
        raise core.MaskingError("masked PDF failed output validation") from exc

    return out, total


def _mask_page(fitz, page, detect_spans: DetectFn) -> int:
    """Mask one page in place. Returns the number of entities detected."""
    text = page.get_text()
    if text.strip():
        return _mask_text_page(page, text, detect_spans)
    # No selectable text: OCR the page image, or treat a truly blank page as
    # nothing to mask.
    if page.get_images(full=True):
        return _mask_scanned_page(fitz, page, detect_spans)
    return 0


def _locate(page, needle: str):
    """Return the rectangles covering *needle* on the page.

    Falls back to searching whitespace-separated tokens when the whole value is
    split across lines (``search_for`` cannot match across a line break).
    """
    rects = page.search_for(needle)
    if rects:
        return rects
    tokens = [t for t in re.split(r"\s+", needle) if len(t) > 1]
    if len(tokens) > 1:
        found = []
        for token in tokens:
            found.extend(page.search_for(token))
        return found
    return []


def _mask_text_page(page, text: str, detect_spans: DetectFn) -> int:
    spans = detect_spans(text)
    if not spans:
        return 0

    count = 0
    located_needles: set[str] = set()
    for start, end, label in spans:
        count += 1
        needle = text[start:end]
        if not needle.strip():
            continue
        # search_for already returns every occurrence of a value, so the first
        # time we see a value we mark all of its rectangles; later spans of the
        # same value are already covered.
        if needle in located_needles:
            continue
        rects = _locate(page, needle)
        if not rects:
            # We detected PII we cannot remove from the page. Fail closed rather
            # than return a PDF that still shows it.
            raise core.MaskingError("could not locate detected PII in the PDF")
        located_needles.add(needle)
        for rect in rects:
            # PyMuPDF shrinks the replacement to fit the covered rectangle, so a
            # long label renders smaller rather than overrunning the line.
            page.add_redact_annot(rect, text=f"<{label}>", fill=(1, 1, 1))

    page.apply_redactions()
    return count


def _mask_scanned_page(fitz, page, detect_spans: DetectFn) -> int:
    if not _ocr_available():
        raise core.MaskingError(
            "scanned PDF requires OCR, which is not available in this deployment"
        )
    import pytesseract
    from PIL import Image
    from pytesseract import Output

    pix = page.get_pixmap(dpi=_OCR_DPI)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        data = pytesseract.image_to_data(
            image, lang=_OCR_LANG, output_type=Output.DICT
        )
    except Exception as exc:  # noqa: BLE001 - missing tesseract binary, etc.
        raise core.MaskingError("OCR failed on the scanned PDF") from exc

    # Rebuild the OCR text with each word's character range and pixel box.
    words: list[tuple[int, int, tuple[int, int, int, int]]] = []
    parts: list[str] = []
    pos = 0
    for i, word in enumerate(data["text"]):
        if not word.strip():
            continue
        start = pos
        end = pos + len(word)
        box = (
            int(data["left"][i]),
            int(data["top"][i]),
            int(data["width"][i]),
            int(data["height"][i]),
        )
        words.append((start, end, box))
        parts.append(word)
        pos = end + 1  # account for the joining space

    full_text = " ".join(parts)
    spans = detect_spans(full_text)
    if not spans:
        return 0

    scale_x = page.rect.width / pix.width
    scale_y = page.rect.height / pix.height
    marked = 0
    for start, end, _label in spans:
        for word_start, word_end, (left, top, width, height) in words:
            if word_start < end and word_end > start:  # overlap
                rect = fitz.Rect(
                    left * scale_x,
                    top * scale_y,
                    (left + width) * scale_x,
                    (top + height) * scale_y,
                )
                page.add_redact_annot(rect, fill=(0, 0, 0))
                marked += 1

    if marked == 0:
        raise core.MaskingError("could not map OCR-detected PII to the page image")

    # Remove the pixels under each box where the PyMuPDF build supports it, so a
    # scanned identifier is truly deleted rather than merely covered.
    pixels_mode = getattr(fitz, "PDF_REDACT_IMAGE_PIXELS", None)
    if pixels_mode is not None:
        page.apply_redactions(images=pixels_mode)
    else:  # older PyMuPDF: redact text layer and paint the boxes over the image
        page.apply_redactions()
        for start, end, _label in spans:
            for word_start, word_end, (left, top, width, height) in words:
                if word_start < end and word_end > start:
                    page.draw_rect(
                        fitz.Rect(
                            left * scale_x,
                            top * scale_y,
                            (left + width) * scale_x,
                            (top + height) * scale_y,
                        ),
                        color=(0, 0, 0),
                        fill=(0, 0, 0),
                    )
    return len(spans)
