import os
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import sys

# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import PDF_DIR, RAW_TEXT_DIR, DOCS_DIR
from datetime import datetime

def extract_from_pdf(pdf_path):
    """Extracts text from a single PDF using pdfplumber with OCR fallback."""
    text_content = []
    metadata = {
        "pages": 0,
        "method": "pdfplumber",
        "words": 0,
        "characters": 0,
        "tables": 0,
        "redaction_tags": 0,
        "ocr_pages": 0
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        metadata["pages"] = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            tables = page.extract_tables()
            metadata["tables"] += len(tables) if tables else 0
            
            if page_text and len(page_text.strip()) >= 30:
                text_content.append(page_text)
            else:
                # Fallback to OCR
                metadata["ocr_pages"] += 1
                metadata["method"] = "mixed (ocr fallback)"
                page_text = ocr_page(pdf_path, i)
                text_content.append(page_text)
                
    full_text = "\n\n".join(text_content)
    metadata["characters"] = len(full_text)
    metadata["words"] = len(full_text.split())
    
    # Very basic count of known redaction tags to satisfy reporting
    tags_to_count = ["PATIENT", "VERANTWOORDELIJKE", "ARTS_", "[ADRES]", "[TELEFOON]", "[URL]", "INSZ", "RIZIV"]
    for tag in tags_to_count:
        metadata["redaction_tags"] += full_text.count(tag)
        
    return full_text, metadata

def ocr_page(pdf_path, page_num, dpi=300):
    """Renders a PDF page to image and runs Tesseract OCR."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    try:
        text = pytesseract.image_to_string(img, lang="nld")
    except pytesseract.TesseractNotFoundError:
        # Fallback if tesseract is not installed
        text = pytesseract.image_to_string(img)
    return text

def run_extraction():
    """Runs extraction on all PDFs and generates report."""
    os.makedirs(RAW_TEXT_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    report_lines = [
        "# Phase 2 — PDF Extraction Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        "| PDF File | Pages | Method | Words | Characters | Tables | Redaction Tags |",
        "|----------|-------|--------|-------|------------|--------|---------------|"
    ]
    
    details_lines = ["", "## Per-Document Details"]
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        file_size = os.path.getsize(pdf_path)
        print(f"Processing {pdf_file}...")
        
        full_text, meta = extract_from_pdf(pdf_path)
        
        # Save raw text
        base_name = os.path.splitext(pdf_file)[0]
        safe_name = base_name.replace(" ", "_").lower()
        out_path = os.path.join(RAW_TEXT_DIR, f"{safe_name}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        report_lines.append(f"| {pdf_file} | {meta['pages']} | {meta['method']} | {meta['words']} | {meta['characters']} | {meta['tables']} | {meta['redaction_tags']} |")
        
        details_lines.extend([
            f"### {pdf_file}",
            f"- **Input**: {file_size} bytes, {meta['pages']} pages",
            f"- **Method**: {meta['method']} (OCR pages: {meta['ocr_pages']})",
            f"- **Tables detected**: {meta['tables']}",
            f"- **Redaction tags roughly counted**: {meta['redaction_tags']}",
            f"- **Output**: `data/raw_text/{safe_name}.txt` ({meta['characters']} chars)",
            f"- **Preview**: {repr(full_text[:500])}..."
        ])
        
    report_content = "\n".join(report_lines + details_lines)
    with open(os.path.join(DOCS_DIR, "phase_2_extraction_report.md"), "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("Phase 2 complete. Outputs in data/raw_text/ and docs/phase_2_extraction_report.md")

if __name__ == "__main__":
    run_extraction()
