import os
import json
import re

def build_hf_dataset():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    data_dir = os.path.join(project_root, "data")
    
    recombined_dir = os.path.join(data_dir, "recombined")
    final_dir = os.path.join(data_dir, "final")
    out_file = os.path.join(data_dir, "hf_ner_dataset.jsonl")
    
    if not os.path.exists(recombined_dir) or not os.path.exists(final_dir):
        print(f"Error: {recombined_dir} or {final_dir} does not exist.")
        return

    json_files = sorted([f for f in os.listdir(recombined_dir) if f.endswith(".json")])
    
    processed = 0
    total_spans = 0
    
    with open(out_file, "w", encoding="utf-8") as f_out:
        for json_name in json_files:
            base_name = json_name.replace(".json", "")
            txt_name = f"{base_name}_report.txt"
            
            json_path = os.path.join(recombined_dir, json_name)
            txt_path = os.path.join(final_dir, txt_name)
            
            if not os.path.exists(txt_path):
                continue
                
            with open(json_path, "r", encoding="utf-8") as f_j:
                variant_data = json.load(f_j)
                
            with open(txt_path, "r", encoding="utf-8") as f_t:
                text = f_t.read()
                
            pii_data = variant_data.get("pii", {})
            spans = []
            
            # Map the json keys to NER labels
            label_map = {
                "patient_naam": "PATIENT_NAME",
                "insz": "BELGIAN_INSZ",
                "riziv_behandelaar": "BELGIAN_RIZIV",
                "arts_naam": "DOCTOR_NAME",
                "arts_verwijzer": "DOCTOR_NAME",
                "ziekenhuis": "HOSPITAL",
                "adres": "ADDRESS",
                "telefoon": "PHONE"
            }
            
            for key, value in pii_data.items():
                if key not in label_map or not value or value == "M" or value == "V":
                    continue
                    
                label = label_map[key]
                # Find all occurrences of this PII string in the text
                pattern = re.compile(re.escape(str(value)))
                for match in pattern.finditer(text):
                    # Check for overlap
                    overlap = False
                    for existing in spans:
                        if max(match.start(), existing["start"]) < min(match.end(), existing["end"]):
                            overlap = True
                            break
                    if not overlap:
                        spans.append({
                            "start": match.start(),
                            "end": match.end(),
                            "label": label
                        })
            
            # Sort spans by start index
            spans.sort(key=lambda x: x["start"])
            
            dataset_entry = {
                "text": text,
                "spans": spans
            }
            
            f_out.write(json.dumps(dataset_entry, ensure_ascii=False) + "\n")
            processed += 1
            total_spans += len(spans)
            
    print(f"Successfully aligned {processed} reports.")
    print(f"Total PII entities found: {total_spans}")
    print(f"Dataset saved to {out_file}")

if __name__ == "__main__":
    build_hf_dataset()
