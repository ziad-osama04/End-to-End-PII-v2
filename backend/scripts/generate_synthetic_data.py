import os
import json
import random
import re
from faker import Faker

fake = Faker('nl_NL')

# Add custom generators for Belgian/Dutch specific PII
def generate_insz():
    return f"{random.randint(10,99)}.{random.randint(1,12):02d}.{random.randint(1,28):02d}-{random.randint(100,999)}.{random.randint(10,99)}"

def generate_hospital():
    hospitals = ["AZORG", "UZ Leuven", "AZ Sint-Jan", "Erasmus MC", "AMC Amsterdam", "Radboudumc"]
    return random.choice(hospitals)

def generate_riziv():
    return f"{random.randint(1,9)}-{random.randint(10000,99999)}-{random.randint(10,99)}-{random.randint(100,999)}"

placeholder_map = {
    "NAME": lambda: fake.name(),
    "FIRST_NAME": lambda: fake.first_name(),
    "LAST_NAME": lambda: fake.last_name(),
    "DOB": lambda: fake.date_of_birth().strftime("%d-%m-%Y"),
    "AGE": lambda: str(random.randint(1, 99)),
    "ADDRESS": lambda: fake.address().replace('\n', ', '),
    "CITY": lambda: fake.city(),
    "PHONE": lambda: fake.phone_number(),
    "INSZ": generate_insz,
    "RIZIV": generate_riziv,
    "HOSPITAL": generate_hospital,
    "DATE": lambda: fake.date_this_year().strftime("%d-%m-%Y"),
    "EMAIL": lambda: fake.email(),
}

def load_templates(data_dir):
    templates = []
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith(".txt"):
                with open(os.path.join(data_dir, filename), "r", encoding="utf-8") as f:
                    templates.append(f.read())
    if not templates:
        # Fallback template
        templates.append("Patiënt: [NAME]\nGeb. datum: [DOB]\nAdres: [ADDRESS]\nINSZ: [INSZ]\nDe patiënt werd gezien in [HOSPITAL].\nTelefoon: [PHONE]")
    return templates

def generate_report(template):
    # Support both [PLACEHOLDER] and {PLACEHOLDER}
    pattern = re.compile(r'\[([A-Z_]+)\]|\{([A-Z_]+)\}')
    text = ""
    spans = []
    last_end = 0
    
    # We will build the text piece by piece
    for match in pattern.finditer(template):
        placeholder = match.group(1) or match.group(2)
        if placeholder in placeholder_map:
            value = placeholder_map[placeholder]()
            
            # Append text up to the match
            text += template[last_end:match.start()]
            
            # Add span
            start_idx = len(text)
            text += value
            end_idx = len(text)
            
            spans.append({
                "start": start_idx,
                "end": end_idx,
                "label": placeholder
            })
            
            last_end = match.end()
            
    text += template[last_end:]
    return {"text": text, "spans": spans}

def main():
    # Adjusted to point to the data directory at the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    data_dir = os.path.join(project_root, "data")
    out_file = os.path.join(data_dir, "synthetic_reports.jsonl")
    
    templates = load_templates(data_dir)
    num_reports = 3000
    
    print(f"Generating {num_reports} synthetic reports from {len(templates)} template(s)...")
    with open(out_file, "w", encoding="utf-8") as f:
        for _ in range(num_reports):
            template = random.choice(templates)
            report_data = generate_report(template)
            f.write(json.dumps(report_data) + "\n")
            
    print(f"Done! Data saved to {out_file}")

if __name__ == "__main__":
    main()
