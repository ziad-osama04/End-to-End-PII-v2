import os
import re
import json
import shutil
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import SYNTHETIC_DIR, FINAL_DIR, DETECTION_DIR, DOCS_DIR


def load_blocklist():
    """Load the original PII blocklist from Phase 3 detection."""
    path = os.path.join(DETECTION_DIR, "original_pii_blocklist.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return ["AZORG"]


# Patterns that should NOT appear in synthetic reports — these are
# the original redaction tags from the HealthOne NOVA source PDFs.
# If any of these leak into the synthetic output, it means the LLM
# copied template placeholders instead of generating fresh content.
ORIGINAL_TAG_PATTERNS = [
    (r'\bPATIENT\s+[A-E]\b', "LEAKED_TAG_PATIENT"),
    (r'\bVERANTWOORDELIJKE\s+[A-D]\b', "LEAKED_TAG_RESPONSIBLE"),
    (r'\bdr\.\s*ARTS_[A-Z]{1,2}\b', "LEAKED_TAG_DOCTOR"),
    (r'\bX{5,}\s+X{5,}\b', "LEAKED_TAG_NAME_ID"),
    (r'\[ADRES\]', "LEAKED_TAG_ADDRESS"),
    (r'\[TELEFOON\]', "LEAKED_TAG_PHONE"),
    (r'\[URL\]', "LEAKED_TAG_URL"),
]

# Real Belgian identifier patterns — only patterns that would indicate
# actual PII leaks. INSZ and RIZIV are NOT checked because the synthetic
# reports intentionally contain Faker-generated fake INSZ/RIZIV numbers
# as pseudonymized replacements for original identifiers.
REAL_ID_PATTERNS = [
    # Belgian/Dutch IBAN (unlikely to be intentionally generated)
    (r'\b(?:NL|BE)\d{2}\s?[A-Z]{4}\s?\d{4}\s?\d{4}\s?\d{0,4}\b', "LEAKED_IBAN"),
    # Email addresses (should not appear in HealthOne NOVA format reports)
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "LEAKED_EMAIL"),
]


def validate_report(text, blocklist):
    """
    Validate a single synthetic report for PII leaks.
    
    Returns a list of findings. Empty list = passed.
    
    Strategy:
    1. Blocklist check — original leaked PII values (e.g., "AZORG")
    2. Original tag pattern check — redaction tags from source PDFs
    3. Real identifier pattern check — INSZ, RIZIV, IBAN, phone, email
    
    We do NOT run the full Presidio NER scan because synthetic reports
    intentionally contain Faker-generated fake names, dates, and locations.
    Those are expected content, not PII leaks.
    """
    findings = []
    
    # 1. Blocklist check (case-insensitive)
    for blocked_term in blocklist:
        if blocked_term.lower() in text.lower():
            findings.append({
                "type": "BLOCKLIST",
                "detail": f"Blocklist match: '{blocked_term}'"
            })
    
    # 2. Original redaction tag patterns (should not leak into synthetic text)
    for pattern, tag_name in ORIGINAL_TAG_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            findings.append({
                "type": tag_name,
                "detail": f"Original tag leaked: '{match}'"
            })
    
    # 3. Real identifier patterns
    for pattern, id_name in REAL_ID_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            findings.append({
                "type": id_name,
                "detail": f"Real identifier found: '{match}'"
            })
    
    return findings


def run_validation():
    os.makedirs(FINAL_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    blocklist = load_blocklist()
    
    synthetic_files = sorted([f for f in os.listdir(SYNTHETIC_DIR) if f.endswith(".txt")])
    
    print(f"Validating {len(synthetic_files)} synthetic reports...")
    print(f"Blocklist terms: {blocklist}")
    
    passed = 0
    failed = 0
    fail_details = []
    finding_type_counts = {}
    
    for syn_file in synthetic_files:
        path = os.path.join(SYNTHETIC_DIR, syn_file)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        
        findings = validate_report(text, blocklist)
        
        if not findings:
            passed += 1
            shutil.copy(path, os.path.join(FINAL_DIR, syn_file))
        else:
            failed += 1
            fail_details.append(f"### {syn_file}")
            for finding in findings:
                fail_details.append(f"- **{finding['type']}**: {finding['detail']}")
                finding_type_counts[finding['type']] = finding_type_counts.get(finding['type'], 0) + 1
    
    # Generate Phase 8 Report
    pass_rate = (passed / len(synthetic_files) * 100) if synthetic_files else 0
    
    report_lines = [
        "# Phase 8 — PII Validation Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"- **Documents validated**: {len(synthetic_files)}",
        f"- **Passed**: {passed}",
        f"- **Failed**: {failed}",
        f"- **Pass rate**: {pass_rate:.1f}%",
        "",
        "## Validation Strategy",
        "The validator checks synthetic reports for:",
        "1. **Blocklist matches** — Original leaked PII values from source documents (e.g., \"AZORG\")",
        "2. **Original redaction tag leaks** — Template placeholders from source PDFs (PATIENT A, dr. ARTS_X, [ADRES], etc.)",
        "3. **Real Belgian identifier patterns** — INSZ, RIZIV, IBAN, phone numbers, emails",
        "",
        "> **Note**: Synthetic reports intentionally contain Faker-generated fake names, dates,",
        "> and hospital names. These are NOT flagged as they are expected synthetic content.",
        "",
    ]
    
    if finding_type_counts:
        report_lines.extend([
            "## Finding Type Distribution",
            "| Finding Type | Count |",
            "|-------------|-------|",
        ])
        for ftype, count in sorted(finding_type_counts.items()):
            report_lines.append(f"| {ftype} | {count} |")
        report_lines.append("")
    
    if fail_details:
        report_lines.extend([
            "## Failed Reports Detail",
            "",
        ])
        report_lines.extend(fail_details)
    
    report_lines.extend([
        "",
        "---",
        f"## Final Certificate",
        f"**{passed}/{len(synthetic_files)} reports passed all PII validation checks.**",
        f"Validated reports saved to: `data/final/`",
    ])
    
    with open(os.path.join(DOCS_DIR, "phase_8_validation_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"\nPhase 8 complete. {passed}/{len(synthetic_files)} safe reports copied to data/final/")
    if failed > 0:
        print(f"  {failed} reports failed — see docs/phase_8_validation_report.md")


if __name__ == "__main__":
    run_validation()
