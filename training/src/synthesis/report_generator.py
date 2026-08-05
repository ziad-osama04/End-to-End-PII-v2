import os
import json
import re
import requests
from datetime import datetime
from tqdm import tqdm
import sys
import time

import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import (RECOMBINED_DIR, SYNTHETIC_DIR, DOCS_DIR, BATCH_SIZE,
                     OPENROUTER_API_KEYS, OPENROUTER_BASE_URL, OPENROUTER_MODEL)


def call_openrouter(system_prompt, user_prompt, max_retries=3):
    """Call OpenRouter API with retry logic."""
    api_key = random.choice(OPENROUTER_API_KEYS)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pii-pipeline",
        "X-Title": "PII Pipeline"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,  # Higher for diversity
        "max_tokens": 2048,
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unexpected response: {data}")
                
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Error: {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    
    raise RuntimeError(f"Failed after {max_retries} retries")


import concurrent.futures

def process_variant(variant_file, prompt_template):
    with open(os.path.join(RECOMBINED_DIR, variant_file), "r", encoding="utf-8") as f:
        variant_data = json.load(f)
    
    # Extract PII to inject into prompt
    pii = variant_data.pop("pii", {})
    specialisme = variant_data.get("specialisme", "Interne geneeskunde")
    
    # Generate a random consultation date in 2025-2026
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.choice([2025, 2026])
    datum = f"{day:02d}/{month:02d}/{year}"
    # Validation date = 1 day later
    vday = min(day + 1, 28)
    validatiedatum = f"{vday:02d}-{month:02d}-{year}"
    
    # Build the prompt with PII placeholders filled in
    clinical_json = json.dumps(variant_data, indent=2, ensure_ascii=False)
    
    prompt = prompt_template
    prompt = prompt.replace("{patient_naam}", pii.get("patient_naam", "Onbekend"))
    prompt = prompt.replace("{geslacht}", pii.get("geslacht", "X"))
    prompt = prompt.replace("{insz}", pii.get("insz", "XX.XX.XX-XXX.XX"))
    prompt = prompt.replace("{riziv}", pii.get("riziv_behandelaar", "X-XXXXX-XX-XXX"))
    prompt = prompt.replace("{arts_naam}", pii.get("arts_naam", "dr. Onbekend"))
    prompt = prompt.replace("{arts_verwijzer}", pii.get("arts_verwijzer", "dr. Onbekend"))
    prompt = prompt.replace("{ziekenhuis}", pii.get("ziekenhuis", "AZ Onbekend"))
    prompt = prompt.replace("{specialisme}", specialisme)
    prompt = prompt.replace("{datum}", datum)
    prompt = prompt.replace("{validatiedatum}", validatiedatum)
    prompt = prompt.replace("{recombined_schema_json}", clinical_json)
    
    try:
        report_text = call_openrouter(
            system_prompt="Je bent een klinisch rapportgenerator. Schrijf ALLEEN plain text, GEEN markdown. Volg het HealthOne NOVA formaat exact.",
            user_prompt=prompt
        )
        
        # Strip Qwen3 thinking tags if present
        if "<think>" in report_text:
            report_text = re.sub(r"<think>.*?</think>", "", report_text, flags=re.DOTALL).strip()
        
        # Strip any markdown formatting the LLM might still produce
        report_text = report_text.replace("**", "")
        report_text = report_text.replace("##", "")
        report_text = report_text.replace("# ", "")
        report_text = re.sub(r"^- ", "  ", report_text, flags=re.MULTILINE)  # bullets to indentation
        report_text = report_text.replace("```", "")
        if "<think>" in report_text:
            report_text = re.sub(r"<think>.*?</think>", "", report_text, flags=re.DOTALL).strip()
        
        base_name = os.path.splitext(variant_file)[0]
        out_path = os.path.join(SYNTHETIC_DIR, f"{base_name}_report.txt")
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report_text)
            
        return (True, variant_file, None)
    except Exception as e:
        return (False, variant_file, str(e))


def run_report_generation():
    os.makedirs(SYNTHETIC_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "prompts", "report_generation.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    variant_files = sorted([f for f in os.listdir(RECOMBINED_DIR) if f.endswith(".json")])
    
    # Checkpointing: skip already-generated reports
    existing_reports = set()
    if os.path.exists(SYNTHETIC_DIR):
        existing_reports = {f.replace("_report.txt", ".json") for f in os.listdir(SYNTHETIC_DIR) if f.endswith("_report.txt")}
    
    remaining = [f for f in variant_files if f not in existing_reports]
    
    print(f"Total variants: {len(variant_files)}, already generated: {len(existing_reports)}, remaining: {len(remaining)}")
    
    report_lines = [
        "# Phase 7 -- Report Generation Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        f"- **Variants to process**: {len(variant_files)}",
        f"- **Already completed (checkpoint)**: {len(existing_reports)}",
        f"- **LLM model**: {OPENROUTER_MODEL} (via OpenRouter)"
    ]
    
    success_count = len(existing_reports)
    fail_count = 0
    
    print(f"Using {len(OPENROUTER_API_KEYS)} threads for concurrent generation...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(OPENROUTER_API_KEYS)) as executor:
        futures = {executor.submit(process_variant, vf, prompt_template): vf for vf in remaining}
    
    for future in tqdm(concurrent.futures.as_completed(futures), total=len(remaining), desc="Generating reports"):
            success, vf, error = future.result()
            if success:
                success_count += 1
            else:
                fail_count += 1
                print(f"\n  Failed for {vf}: {error}")
            
    report_lines.append(f"- **Successfully generated**: {success_count}")
    report_lines.append(f"- **Failed**: {fail_count}")
    
    with open(os.path.join(DOCS_DIR, "phase_7_generation_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"\nPhase 7 complete. {success_count} reports in data/synthetic_reports/")

if __name__ == "__main__":
    run_report_generation()
