import os
import json
import re
import random
from datetime import datetime, timedelta
from faker import Faker
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import RAW_TEXT_DIR, DETECTION_DIR, PSEUDONYMIZED_DIR, DOCS_DIR

fake_be = Faker('nl_BE')
fake_nl = Faker('nl_NL')

# De-identification policy for bare spaCy PERSON/ORGANIZATION/LOCATION hits.
# These fire on clinical terms (disease eponyms, medications, lab units) as often
# as on real names. Precise de-id (False) leaves them untouched so clinical text
# is preserved and no fake PII is injected into medical positions. Set True only
# for an aggressive "mask anything name-shaped" policy.
PSEUDONYMIZE_FREETEXT = False

# Realistic Belgian hospital names
FAKE_HOSPITALS = [
    "AZ Sint-Lucas", "AZ Maria Middelares", "UZ Brussel",
    "AZ Groeninge", "AZ Delta", "AZ Nikolaas",
    "AZ Sint-Jan", "AZ Turnhout", "AZ Glorieux",
    "AZ Jan Portaels", "AZ Vesalius", "AZ Rivierenland",
]

# Realistic Belgian medical specialties for verwijzingen
SPECIALTIES = [
    "Gastro-enterologie", "Cardiologie", "Orthopedie",
    "Pneumologie", "Oftalmologie", "Neurologie",
    "Dermatologie", "Urologie", "Gynaecologie",
]


def deduplicate_spans(pii_map):
    """Remove overlapping detections, keeping the one with highest score.
    
    When TAGGED_* (score=1.0) and spaCy ORGANIZATION (score=0.85) both detect 
    the same span (e.g. INSZXXXXXXXXXXX), we keep only the TAGGED_ one.
    """
    # Sort by start, then by score descending
    sorted_items = sorted(pii_map, key=lambda x: (x["start"], -x["score"]))
    
    result = []
    for item in sorted_items:
        # Check if this item overlaps with any already-accepted item
        overlaps = False
        for accepted in result:
            # Two spans overlap if one starts before the other ends
            if item["start"] < accepted["end"] and item["end"] > accepted["start"]:
                overlaps = True
                break
        if not overlaps:
            result.append(item)
    
    return result


class DocumentPseudonymizer:
    """Handles pseudonymization for a single document with consistent replacements."""
    
    def __init__(self, seed=42):
        self.replacements = {}
        Faker.seed(seed)
        random.seed(seed)
        
    def _generate_insz(self):
        """Generate a realistic Belgian INSZ number: YY.MM.DD-SEQ.CHK"""
        yy = random.randint(40, 99)
        mm = random.randint(1, 12)
        dd = random.randint(1, 28)
        seq = random.randint(1, 997)
        base_num = int(f"{yy:02d}{mm:02d}{dd:02d}{seq:03d}")
        chk = 97 - (base_num % 97)
        return f"{yy:02d}.{mm:02d}.{dd:02d}-{seq:03d}.{chk:02d}"
    
    def _generate_riziv(self):
        """Generate a realistic Belgian RIZIV number: X-XXXXX-XX-XXX"""
        return f"{random.randint(1,9)}-{random.randint(10000,99999):05d}-{random.randint(10,99):02d}-{random.randint(100,999):03d}"
        
    def get_replacement(self, entity_type, original_value):
        """Get or generate a replacement for a detected PII entity."""
        if original_value in self.replacements:
            return self.replacements[original_value]
            
        new_val = original_value
        
        # =============================================
        # Track A: Tagged PII (already redacted in PDFs)
        # =============================================
        if entity_type == "TAGGED_PATIENT":
            # Replace "PATIËNT A" with a realistic Dutch/Belgian name
            new_val = fake_be.name()
            
        elif entity_type == "TAGGED_RESPONSIBLE":
            # Replace "Verantwoordelijke A" with a realistic name
            new_val = "dr. " + fake_be.last_name()
            
        elif entity_type == "TAGGED_DOCTOR":
            # Replace "dr. ARTS_A" or standalone "ARTS_A" with "dr. LastName"
            new_val = "dr. " + fake_be.last_name()
            
        elif entity_type == "TAGGED_NATIONAL_ID":
            # INSZXXXXXXXXXXX → realistic INSZ number (15 chars → 14 chars)
            new_val = self._generate_insz()
            
        elif entity_type == "TAGGED_PROVIDER_ID":
            # RIZIVXXXXXXXXXXX → realistic RIZIV number (16 chars → 15 chars)
            new_val = self._generate_riziv()
            
        elif entity_type == "TAGGED_NAME_ID":
            new_val = fake_be.name()
            
        elif entity_type == "TAGGED_ADDRESS":
            new_val = fake_be.street_address() + ", " + fake_be.postcode() + " " + fake_be.city()
            
        elif entity_type == "TAGGED_PHONE":
            new_val = fake_be.phone_number()
            
        elif entity_type == "TAGGED_URL":
            new_val = "www." + fake_be.domain_name()
            
        elif entity_type == "TAGGED_HOSPITAL":
            new_val = random.choice(FAKE_HOSPITALS)
            
        # =============================================
        # Track B: Leaked PII (newly detected)
        # =============================================
        elif entity_type == "LEAKED_DOB":
            new_val = fake_be.date_of_birth(minimum_age=18, maximum_age=90).strftime("%d-%m-%Y")
            
        elif entity_type == "LEAKED_AGE":
            nums = re.findall(r"\d+", original_value)
            if nums:
                age = int(nums[0])
                new_age = max(1, age + random.randint(-5, 5))
                new_val = original_value.replace(nums[0], str(new_age))
                
        elif entity_type in ("LEAKED_HEIGHT", "LEAKED_WEIGHT", "LEAKED_BMI"):
            nums = re.findall(r"\d+", original_value)
            if nums:
                val = int(nums[0])
                new_val = original_value.replace(nums[0], str(max(1, val + random.randint(-5, 5))))
                
        elif entity_type == "LEAKED_RACE":
            new_val = "[ETNICITEIT]"
            
        elif entity_type == "LEAKED_DEPT":
            new_val = random.choice(SPECIALTIES)
            
        elif entity_type == "LEAKED_HOSPITAL":
            new_val = random.choice(FAKE_HOSPITALS)
            
        elif entity_type == "BELGIAN_INSZ":
            new_val = self._generate_insz()
            
        elif entity_type == "PHONE_NUMBER_NL_BE":
            new_val = fake_be.phone_number()
            
        elif entity_type == "IBAN_NL_BE":
            new_val = fake_be.iban()
            
        # =============================================
        # Generic spaCy entities. They fire on clinical terms (disease eponyms
        # like "Von Willebrand", medications, lab units) as often as on real
        # names. Under precise de-id they are LEFT UNCHANGED -- replacing them
        # injects fake PII into clinical text and trains the model to mask
        # medical terms. Enable PSEUDONYMIZE_FREETEXT for the aggressive policy.
        # =============================================
        elif entity_type in ("PERSON", "ORGANIZATION", "LOCATION"):
            if PSEUDONYMIZE_FREETEXT:
                new_val = {
                    "PERSON": fake_be.name,
                    "ORGANIZATION": fake_be.company,
                    "LOCATION": fake_be.city,
                }[entity_type]()
            # precise de-id: keep the clinical term (new_val stays original)
        elif entity_type == "DATE_TIME":
            # Don't replace clinical dates
            new_val = original_value
            
        self.replacements[original_value] = new_val
        return new_val


def run_pseudonymization():
    os.makedirs(PSEUDONYMIZED_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    txt_files = [f for f in os.listdir(RAW_TEXT_DIR) if f.endswith(".txt")]
    
    report_lines = [
        "# Phase 4 -- Pseudonymization Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"- **Documents processed**: {len(txt_files)}",
        "",
        "## Replacements",
        "| Document | Entity Type | Original Value | Replacement |",
        "|----------|-------------|----------------|-------------|"
    ]
    
    total_replacements = 0
    total_unchanged = 0
    total_deduped = 0
    
    for txt_file in txt_files:
        base = os.path.splitext(txt_file)[0]
        map_path = os.path.join(DETECTION_DIR, f"{base}_pii_map.json")
        
        if not os.path.exists(map_path):
            print(f"Warning: No PII map found for {txt_file}")
            continue
            
        with open(os.path.join(RAW_TEXT_DIR, txt_file), "r", encoding="utf-8") as f:
            text = f.read()
            
        with open(map_path, "r", encoding="utf-8") as f:
            pii_map = json.load(f)
        
        # Deduplicate overlapping spans — keep highest-score detection
        original_count = len(pii_map)
        pii_map = deduplicate_spans(pii_map)
        total_deduped += (original_count - len(pii_map))
            
        # Replace from end to start to preserve character offsets
        pii_map_sorted = sorted(pii_map, key=lambda x: x["start"], reverse=True)
        pseudo = DocumentPseudonymizer(seed=hash(txt_file) % 10000)
        
        for item in pii_map_sorted:
            orig = item["value"]
            entity_type = item["entity_type"]
            repl = pseudo.get_replacement(entity_type, orig)
            
            if repl != orig:
                text = text[:item["start"]] + repl + text[item["end"]:]
                report_lines.append(f"| {txt_file} | {entity_type} | `{orig}` | `{repl}` |")
                total_replacements += 1
            else:
                total_unchanged += 1
            
        out_path = os.path.join(PSEUDONYMIZED_DIR, txt_file)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
            
    report_lines.insert(5, f"- **Total replacements made**: {total_replacements}")
    report_lines.insert(6, f"- **Entities left unchanged (dates, etc.)**: {total_unchanged}")
    report_lines.insert(7, f"- **Duplicate overlapping detections removed**: {total_deduped}")
            
    with open(os.path.join(DOCS_DIR, "phase_4_pseudonymization_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Phase 4 complete. {total_replacements} replacements, {total_unchanged} unchanged, {total_deduped} deduped")

if __name__ == "__main__":
    run_pseudonymization()
