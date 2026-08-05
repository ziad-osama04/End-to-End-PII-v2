import os
import json
from datetime import datetime
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
import sys

# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import RAW_TEXT_DIR, DETECTION_DIR, DOCS_DIR
from src.detection.tag_parser import get_tag_recognizers
from src.detection.dutch_regex import get_dutch_regex_recognizers

# Medical / clinical terms that spaCy wrongly tags as PII.
# We skip any detection whose raw text matches one of these.
MEDICAL_ALLOWLIST = {
    # Diseases & conditions
    "epididymitis", "colitis", "fissuur", "darmkanker", "hypertonie",
    "constipatie", "diabetes", "diabetisch", "retinopathie", "neuropathie",
    "glaucoom", "cataract", "macula", "maculadegeneratie",
    # Anatomy
    "supraspinatuspees", "sfincter", "bekkenbodem", "bekkenbodemtonus",
    "subscapularis", "biceps", "supraspinatus", "infraspinatus",
    "m. subscapularis", "m. biceps caput", "m. infraspinatus",
    # Medication & treatment
    "diltiazemzalf", "laxativum", "depomedrol", "sipralexa", "metformine",
    "lambipol", "depakine", "pantomed", "panto", "asaflow", "atorstatineg",
    "d-cure", "insuline toujeo", "insuline lyumjev", "cose", "trianal",
    # Clinical procedures & abbreviations
    "eswt", "coloscopie", "plethysmogr", "transfertest", "spirometrie",
    "longfunctie", "humphrey", "oct", "oogdruk", "visus",
    # Lab / measurement terms
    "kco", "tlc", "fvc", "fev1", "pef", "fef", "mif", "tgv", "raw",
    "pleth", "meas", "bmi", "ssp", "ods", "sc", "box", "vc",
    "mmol", "kpa", "l/sec",
    # Common Dutch words wrongly tagged
    "grootvader", "paternele", "familiaal", "voorlopig", "fors",
    "painful", "significant", "ijzer", "artsen", "patiente", "iom",
    "weekdagen", "fl inj", "4 weken", "1/w", "2/d",
    # Hospital department / context
    "longv", "icht", "ras",
    # Time references that aren't PII
    "10:18", "8u", "12u", "18u", "22u", "8.30u", "8u 12u",
}

def is_medical_term(value):
    """Check if a detected value is actually a medical term (false positive)."""
    clean = value.strip().lower()
    if clean in MEDICAL_ALLOWLIST:
        return True
    # Skip very short detections (2 chars or less) — typically abbreviations
    if len(clean) <= 2:
        return True
    # Skip pure numbers and floating point numbers (often picked up by spaCy)
    try:
        float(clean.replace(',', '.'))
        return True
    except ValueError:
        pass
    # Skip units or purely symbolic strings (e.g., mmol/min/kPa/L)
    import re
    if not re.search(r'[a-zA-Z]{3,}', clean):
        return True
    return False

def build_analyzer():
    """Builds and configures the Presidio AnalyzerEngine with custom recognizers."""
    # 1. NLP Engine (spaCy)
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "nl", "model_name": "nl_core_news_lg"}]
    })
    nlp_engine = provider.create_engine()
    
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["nl"]
    )
    
    # 2. Add Layer 0: Tag Recognizers (highest priority, score=1.0)
    for recognizer in get_tag_recognizers():
        analyzer.registry.add_recognizer(recognizer)
        
    # 3. Add Layer 3: Dutch/Belgian Regex Recognizers (Leaked + Standard)
    for recognizer in get_dutch_regex_recognizers():
        analyzer.registry.add_recognizer(recognizer)
    
    return analyzer

def run_detection():
    os.makedirs(DETECTION_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    analyzer = build_analyzer()
    
    txt_files = [f for f in os.listdir(RAW_TEXT_DIR) if f.endswith(".txt")]
    
    # Reporting stats
    total_tagged = 0
    total_leaked = 0
    total_skipped = 0
    tag_counts = {}
    leak_list = []
    
    for txt_file in txt_files:
        print(f"Detecting PII in {txt_file}...")
        with open(os.path.join(RAW_TEXT_DIR, txt_file), "r", encoding="utf-8") as f:
            text = f.read()
            
        results = analyzer.analyze(text=text, language="nl")
        
        # Format results, filtering out false positives
        output_results = []
        for res in results:
            raw_value = text[res.start:res.end]
            
            # Skip medical false positives from spaCy
            if res.entity_type in ("PERSON", "ORGANIZATION", "LOCATION", "NRP", "MISC"):
                if is_medical_term(raw_value):
                    total_skipped += 1
                    continue
            
            # Determine if it's a TAGGED or LEAKED entity
            if res.entity_type.startswith("TAGGED_"):
                total_tagged += 1
                tag_counts[res.entity_type] = tag_counts.get(res.entity_type, 0) + 1
            elif res.entity_type.startswith("LEAKED_"):
                total_leaked += 1
                leak_list.append({
                    "doc": txt_file,
                    "category": res.entity_type,
                    "value": raw_value,
                    "score": res.score
                })
                
            output_results.append({
                "entity_type": res.entity_type,
                "start": res.start,
                "end": res.end,
                "score": res.score,
                "value": raw_value
            })
            
        # Sort by start offset
        output_results = sorted(output_results, key=lambda x: x["start"])
        
        out_path = os.path.join(DETECTION_DIR, f"{os.path.splitext(txt_file)[0]}_pii_map.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_results, f, indent=2, ensure_ascii=False)
            
    # Generate Phase 3 Report
    report_lines = [
        "# Phase 3 — PII Detection Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"- **Tagged PII entities (already redacted)**: {total_tagged}",
        f"- **Leaked PII entities (newly detected)**: {total_leaked}",
        f"- **Total PII entities**: {total_tagged + total_leaked}",
        f"- **False positives skipped (medical terms)**: {total_skipped}",
        f"- **Documents processed**: {len(txt_files)}",
        "",
        "## Tagged PII Inventory (Table 1 Validation)",
        "| Category | Count |",
        "|----------|-------|"
    ]
    
    for cat, count in sorted(tag_counts.items()):
        report_lines.append(f"| {cat} | {count} |")
        
    report_lines.extend([
        "",
        "## ⚠️ Leaked PII Detected (Table 2)",
        "| Document | Category | Value Found | Confidence |",
        "|----------|----------|-------------|------------|"
    ])
    
    # Save a blocklist of leaked raw values to use in Phase 8
    blocklist = set()
    
    for leak in sorted(leak_list, key=lambda x: x["doc"]):
        report_lines.append(f"| {leak['doc']} | {leak['category']} | `{leak['value']}` | {leak['score']:.2f} |")
        blocklist.add(leak["value"])
        
    # Always block AZORG
    blocklist.add("AZORG")
    
    with open(os.path.join(DETECTION_DIR, "original_pii_blocklist.json"), "w", encoding="utf-8") as f:
        json.dump(list(blocklist), f, indent=2, ensure_ascii=False)
        
    with open(os.path.join(DOCS_DIR, "phase_3_detection_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Phase 3 complete. Tagged={total_tagged}, Leaked={total_leaked}, Skipped={total_skipped}")

if __name__ == "__main__":
    run_detection()
