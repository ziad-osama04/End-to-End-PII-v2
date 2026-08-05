import os
import json
import requests
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
import sys
import time

import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import (PSEUDONYMIZED_DIR, SCHEMAS_DIR, DOCS_DIR, 
                     OPENROUTER_API_KEYS, OPENROUTER_BASE_URL, OPENROUTER_MODEL)

def flatten_item(item):
    """Flatten a dict like {'naam': 'Asaflow', 'dosering': '80mg'} into a single string."""
    if isinstance(item, str):
        return item
    elif isinstance(item, dict):
        parts = [str(v) for v in item.values() if v]
        return " | ".join(parts)
    else:
        return str(item)

class ClinicalSchema(BaseModel):
    geslacht: Optional[str] = Field(None, description="M/V/X")
    leeftijdscategorie: Optional[str] = Field(None, description="Leeftijdscategorie, bijv 50-59")
    klachten: List[str] = Field(default_factory=list)
    diagnoses: List[str] = Field(default_factory=list)
    medicatie: list = Field(default_factory=list)  # Accept any type, normalize later
    lab_resultaten: list = Field(default_factory=list)  # Accept any type, normalize later
    anamnese_type: Optional[str] = Field(None)
    behandelplan: Optional[str] = Field(None)
    verwijzingen: List[str] = Field(default_factory=list)
    allergieen: List[str] = Field(default_factory=list)
    
    def normalized_dump(self):
        """Return dict with all list items flattened to strings."""
        data = self.model_dump()
        data["medicatie"] = [flatten_item(m) for m in data["medicatie"]]
        data["lab_resultaten"] = [flatten_item(r) for r in data["lab_resultaten"]]
        return data


def call_openrouter(system_prompt, user_prompt, json_mode=False, max_retries=3):
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
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    
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
                raise ValueError(f"Unexpected response structure: {data}")
                
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


def run_schema_extraction():
    os.makedirs(SCHEMAS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "prompts", "schema_extraction.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    txt_files = [f for f in os.listdir(PSEUDONYMIZED_DIR) if f.endswith(".txt")]
    
    report_lines = [
        "# Phase 5 — Schema Extraction Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Summary",
        f"- **Documents processed**: {len(txt_files)}",
        f"- **LLM model**: {OPENROUTER_MODEL} (via OpenRouter)",
        ""
    ]
    
    for txt_file in txt_files:
        print(f"Extracting schema for {txt_file}...")
        with open(os.path.join(PSEUDONYMIZED_DIR, txt_file), "r", encoding="utf-8") as f:
            text = f.read()
            
        prompt = prompt_template.replace("{pseudonymized_text}", text)
        
        try:
            response_text = call_openrouter(
                system_prompt="Je bent een AI die enkel JSON format output teruggeeft. Geef geen extra tekst, alleen valide JSON.",
                user_prompt=prompt,
                json_mode=True
            )
            
            # Strip any markdown code fences if present
            clean = response_text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()
            
            # Parse and validate with Pydantic
            schema_data = json.loads(clean)
            validated = ClinicalSchema(**schema_data)
            out_data = validated.normalized_dump()
            
            status = "[OK] Success"
            print(f"  [OK] {txt_file}: extracted {len(out_data.get('diagnoses', []))} diagnoses, {len(out_data.get('medicatie', []))} medications")
        except Exception as e:
            print(f"  [FAIL] Extraction failed for {txt_file}: {e}")
            out_data = {"error": str(e)}
            status = "[FAIL] Failed"
            
        out_path = os.path.join(SCHEMAS_DIR, f"{os.path.splitext(txt_file)[0]}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2, ensure_ascii=False)
            
        report_lines.append(f"- {txt_file}: {status}")
        
    with open(os.path.join(DOCS_DIR, "phase_5_schema_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print("Phase 5 complete. Outputs in data/schemas/")

if __name__ == "__main__":
    run_schema_extraction()
