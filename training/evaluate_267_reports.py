import json
import os
import sys
from tqdm import tqdm
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.detection.pii_detector import build_analyzer, is_medical_term

def main():
    final_dir = "data/final"
    recombined_dir = "data/recombined"
    
    txt_files = sorted([f for f in os.listdir(final_dir) if f.endswith(".txt")])
    if not txt_files:
        print("No files found in data/final")
        return
        
    print("Initializing spaCy & Regex Analyzer...")
    analyzer = build_analyzer()
    
    total_injected = 0
    total_found = 0
    total_detected = 0
    
    type_metrics = {}
    
    for txt_file in tqdm(txt_files, desc="Evaluating 267 reports"):
        base_name = txt_file.replace("_report.txt", "")
        json_path = os.path.join(recombined_dir, f"{base_name}.json")
        txt_path = os.path.join(final_dir, txt_file)
        
        if not os.path.exists(json_path):
            continue
            
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        # Run analyzer
        results = analyzer.analyze(text=text, language="nl")
        detected_spans = []
        for res in results:
            raw_value = text[res.start:res.end]
            if res.entity_type in ("PERSON", "ORGANIZATION", "LOCATION", "NRP", "MISC"):
                if is_medical_term(raw_value):
                    continue
            detected_spans.append((res.start, res.end, res.entity_type))
            
        total_detected += len(detected_spans)
            
        # Ground truth values from PII dict
        pii_dict = data.get("pii", {})
        
        # Injected PII types to evaluate
        targets = {
            "PATIENT_NAME": pii_dict.get("patient_naam"),
            "INSZ": pii_dict.get("insz"),
            "RIZIV": pii_dict.get("riziv_behandelaar"),
            "DOCTOR_NAME": pii_dict.get("arts_naam"),
            "DOCTOR_REF": pii_dict.get("arts_verwijzer"),
            "HOSPITAL": pii_dict.get("ziekenhuis"),
            "ADDRESS": pii_dict.get("adres"),
            "PHONE": pii_dict.get("telefoon"),
        }
        
        for pii_type, value in targets.items():
            if not value:
                continue
                
            # Check if this exact string actually appears in the text
            # The LLM sometimes hallucinates slight variations, so we check exact substrings
            # Note: A real LLM might split names or reformat INSZ, but for strict evaluation we look for the exact injected value.
            starts = [m.start() for m in re.finditer(re.escape(value), text)]
            
            for start in starts:
                end = start + len(value)
                total_injected += 1
                
                if pii_type not in type_metrics:
                    type_metrics[pii_type] = {"total": 0, "found": 0}
                type_metrics[pii_type]["total"] += 1
                
                # Check if any detected span overlaps with this occurrence
                found = False
                for d_start, d_end, d_type in detected_spans:
                    if max(0, min(end, d_end) - max(start, d_start)) > 0:
                        found = True
                        break
                        
                if found:
                    total_found += 1
                    type_metrics[pii_type]["found"] += 1

    recall = total_found / total_injected if total_injected > 0 else 0
    
    print("\n--- RECALL SCORES FOR 267 SYNTHETIC REPORTS ---")
    print(f"Total files: {len(txt_files)}")
    print(f"Total injected PII values actually present in generated text: {total_injected}")
    print(f"Total successfully detected by spaCy/Regex engine: {total_found}")
    print(f"Overall Recall: {recall*100:.2f}%")
    
    print("\n--- RECALL BY CATEGORY ---")
    for t_name, metrics in sorted(type_metrics.items(), key=lambda x: x[1]["found"]/x[1]["total"] if x[1]["total"] > 0 else 0):
        t_tot = metrics["total"]
        t_f = metrics["found"]
        t_rec = t_f / t_tot if t_tot > 0 else 0
        print(f"{t_name:<15} : {t_rec*100:>5.1f}% ({t_f}/{t_tot})")
        
    print("\nNote: Precision cannot be accurately calculated because the LLM generates dates/ages that are valid PII but not in the injected PII schema dictionary.")

if __name__ == "__main__":
    main()
