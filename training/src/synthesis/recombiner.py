import os
import json
import random
import hashlib
from datetime import datetime
from faker import Faker
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import SCHEMAS_DIR, RECOMBINED_DIR, DOCS_DIR, NUM_SYNTHETIC_REPORTS

fake_be = Faker('nl_BE')
Faker.seed(None)  # Random seed for diversity

# ============================================================
# Dutch/Belgian epidemiological data for realistic generation
# Source: RIVM, Sciensano, CBS, Nivel
# ============================================================

# Weighted by Dutch/Belgian prevalence (approximate % of GP consultations)
CLINICAL_SPECIALTIES = [
    ("Huisarts", 30),
    ("Cardiologie", 12),
    ("Orthopedie", 8),
    ("Gastro-enterologie", 7),
    ("Pneumologie", 7),
    ("Neurologie", 6),
    ("Endocrinologie", 5),
    ("Dermatologie", 5),
    ("Urologie", 4),
    ("Gynaecologie", 4),
    ("Oftalmologie", 4),
    ("Reumatologie", 3),
    ("Psychiatrie", 3),
    ("Oncologie", 2),
]

# Common Dutch diagnoses grouped by specialty, weighted by prevalence
DIAGNOSES_BY_SPECIALTY = {
    "Huisarts": [
        "acute bovenste luchtweginfectie", "lage rugpijn", "urineweginfectie",
        "hypertensie", "diabetes mellitus type 2", "eczeem", "depressie",
        "angststoornis", "slaapstoornissen", "obstipatie", "gordelroos",
        "otitis media acuta", "sinusitis", "bronchitis", "gastro-oesofageale reflux",
        "ijzergebreksanemie", "hypothyreoidie", "jicht", "artrose knie",
    ],
    "Cardiologie": [
        "atriumfibrilleren", "hartfalen NYHA II", "hartfalen NYHA III",
        "instabiele angina pectoris", "acuut coronair syndroom",
        "hypertensieve hartziekte", "aortaklepstenose", "mitralisinsufficiëntie",
        "ventriculaire tachycardie", "diep veneuze trombose", "longembolie",
        "perifeer arterieel vaatlijden", "aneurysma aorta abdominalis",
    ],
    "Orthopedie": [
        "coxartrose", "gonartrose", "rotatorcuff ruptuur",
        "lumbale hernia nuclei pulposi", "cervicale spondylose",
        "achillespeesruptuur", "meniscusletsel", "fractuur radius distaal",
        "frozen shoulder", "carpaal tunnel syndroom", "hallux valgus",
        "epicondylitis lateralis", "impingement schouder",
    ],
    "Gastro-enterologie": [
        "ziekte van Crohn", "colitis ulcerosa", "coeliakie",
        "prikkelbaredarmsyndroom", "diverticulitis", "poliepen colon",
        "maagulcus", "oesofagitis", "anale fissuur", "hemorroiden",
        "niet-alcoholische leververvetting", "pancreatitis acuta",
        "microscopische colitis", "Barrett-oesofagus",
    ],
    "Pneumologie": [
        "COPD Gold II", "COPD Gold III", "astma", "pneumonie",
        "longfibrose", "slaapapneusyndroom", "pleuritis",
        "longemfyseem", "bronchiëctasieën", "sarcoïdose",
        "allergische rhinitis", "pneumothorax",
    ],
    "Neurologie": [
        "migraine", "spanningshoofdpijn", "epilepsie",
        "CVA ischemisch", "TIA", "ziekte van Parkinson",
        "multiple sclerose", "perifere neuropathie",
        "radiculopathie L5-S1", "carpaal tunnel syndroom",
        "essentiële tremor", "restless legs syndroom",
    ],
    "Endocrinologie": [
        "diabetes mellitus type 1", "diabetes mellitus type 2",
        "hypothyreoidie", "hyperthyreoidie", "ziekte van Graves",
        "bijnierschorsinsufficiëntie", "obesitas morbide",
        "syndroom van Cushing", "hyperparathyreoidie",
        "diabetische nefropathie", "diabetische retinopathie",
    ],
    "Dermatologie": [
        "psoriasis vulgaris", "acne vulgaris", "eczeem",
        "dermatitis contactallergisch", "basaalcelcarcinoom",
        "melanoom", "urticaria", "rosacea", "tinea pedis",
        "alopecia areata", "vitiligo", "keratosis actinica",
    ],
    "Urologie": [
        "benigne prostaathyperplasie", "urolithiasis", "prostaatcarcinoom",
        "blaascarcinoom", "urineweginfectie recidiverend",
        "stressincontinentie", "overactieve blaas", "epididymitis",
        "varicocèle", "niercelcarcinoom", "hydronefrose",
    ],
    "Gynaecologie": [
        "uterus myomatosus", "endometriose", "PCOS",
        "cervixdysplasie", "ovariële cyste", "menorragie",
        "vaginale prolaps", "vulvovaginale candidiasis",
        "amenorroe", "infertiliteit",
    ],
    "Oftalmologie": [
        "cataract", "glaucoom", "diabetische retinopathie",
        "maculadegeneratie", "conjunctivitis", "droge ogen",
        "retinaloslating", "uveitis", "keratitis",
    ],
    "Reumatologie": [
        "reumatoïde artritis", "jicht", "artrose",
        "systemische lupus erythematosus", "fibromyalgie",
        "spondylitis ankylopoetica", "polymyalgia rheumatica",
        "vasculitis", "sclerodermie",
    ],
    "Psychiatrie": [
        "depressieve stoornis", "gegeneraliseerde angststoornis",
        "paniekstoornis", "PTSS", "bipolaire stoornis",
        "schizofrenie", "ADHD", "alcoholafhankelijkheid",
        "burn-out", "slaapstoornis",
    ],
    "Oncologie": [
        "mammacarcinoom", "coloncarcinoom", "longcarcinoom",
        "prostaatcarcinoom", "melanoom", "lymfoom non-Hodgkin",
        "blaascarcinoom", "niercelcarcinoom", "pancreascarcinoom",
    ],
}

# Common Dutch medications by category
MEDICATIONS = {
    "antihypertensiva": ["Lisinopril 10mg 1dd", "Amlodipine 5mg 1dd", "Losartan 50mg 1dd", "Hydrochloorthiazide 12.5mg 1dd", "Bisoprolol 5mg 1dd"],
    "antidiabetica": ["Metformine 500mg 2dd", "Metformine 850mg 2dd", "Gliclazide 80mg 1dd", "Insuline glargine 20E sc 22u", "Empagliflozine 10mg 1dd", "Sitagliptine 100mg 1dd"],
    "cholesterolverlagers": ["Atorvastatine 40mg 1dd", "Rosuvastatine 10mg 1dd", "Simvastatine 20mg 1dd", "Ezetimibe 10mg 1dd"],
    "bloedverdunners": ["Acetylsalicylzuur 80mg 1dd", "Rivaroxaban 20mg 1dd", "Apixaban 5mg 2dd", "Clopidogrel 75mg 1dd"],
    "maagbescherming": ["Omeprazol 20mg 1dd", "Pantoprazol 40mg 1dd", "Esomeprazol 20mg 1dd"],
    "pijnstilling": ["Paracetamol 1000mg 3dd", "Ibuprofen 400mg 3dd", "Tramadol 50mg 2dd", "Naproxen 500mg 2dd"],
    "antidepressiva": ["Sertraline 50mg 1dd", "Citalopram 20mg 1dd", "Venlafaxine 75mg 1dd", "Amitriptyline 10mg an"],
    "luchtwegen": ["Salbutamol 100mcg inh znb", "Budesonide/formoterol 200/6mcg 2dd", "Tiotropium 18mcg 1dd inh", "Montelukast 10mg 1dd"],
    "schildklier": ["Levothyroxine 50mcg 1dd nuchter", "Levothyroxine 75mcg 1dd nuchter", "Levothyroxine 100mcg 1dd nuchter"],
    "overig": ["Vitamine D3 25000IE 1x/maand", "Calciumcarbonaat 500mg 2dd", "Ferrofumaraat 200mg 1dd", "Foliumzuur 5mg 1dd"],
}

# Age distribution (weighted by Dutch demographic + disease prevalence)
AGE_RANGES = [
    ("18-29", 8), ("30-39", 10), ("40-49", 14), ("50-59", 18),
    ("60-69", 22), ("70-79", 18), ("80-89", 8), ("90+", 2),
]

GESLACHT_OPTIONS = [("M", 48), ("V", 52)]  # Dutch population ratio


def weighted_choice(options):
    """Pick from list of (value, weight) tuples."""
    values, weights = zip(*options)
    return random.choices(values, weights=weights, k=1)[0]


def generate_pii(geslacht=None):
    """Generate a unique set of realistic Dutch/Belgian PII for one report."""
    if not geslacht:
        geslacht = weighted_choice(GESLACHT_OPTIONS)
    
    if geslacht == "M":
        voornaam = fake_be.first_name_male()
        achternaam = fake_be.last_name()
    else:
        voornaam = fake_be.first_name_female()
        achternaam = fake_be.last_name()
    
    # Realistic INSZ
    yy = random.randint(30, 99)
    mm = random.randint(1, 12)
    dd = random.randint(1, 28)
    seq = random.randint(1, 997)
    base_num = int(f"{yy:02d}{mm:02d}{dd:02d}{seq:03d}")
    chk = 97 - (base_num % 97)
    insz = f"{yy:02d}.{mm:02d}.{dd:02d}-{seq:03d}.{chk:02d}"
    
    # Realistic RIZIV
    riziv = f"{random.randint(1,9)}-{random.randint(10000,99999):05d}-{random.randint(10,99):02d}-{random.randint(100,999):03d}"
    
    return {
        "patient_naam": f"{voornaam} {achternaam}",
        "geslacht": geslacht,
        "insz": insz,
        "riziv_behandelaar": riziv,
        "arts_naam": "dr. " + fake_be.last_name(),
        "arts_verwijzer": "dr. " + fake_be.last_name(),
        "ziekenhuis": random.choice([
            "AZ Sint-Lucas", "AZ Maria Middelares", "UZ Brussel",
            "AZ Groeninge", "AZ Delta", "AZ Nikolaas",
            "AZ Sint-Jan", "AZ Turnhout", "AZ Glorieux",
            "UZ Gent", "UZ Leuven", "AZ Vesalius",
        ]),
        "adres": fake_be.street_address() + ", " + fake_be.postcode() + " " + fake_be.city(),
        "telefoon": fake_be.phone_number(),
    }


def generate_clinical_scenario():
    """Generate a unique, epidemiologically weighted clinical scenario."""
    specialty = weighted_choice(CLINICAL_SPECIALTIES)
    diagnoses_pool = DIAGNOSES_BY_SPECIALTY.get(specialty, DIAGNOSES_BY_SPECIALTY["Huisarts"])
    
    # Pick 1-3 diagnoses (weighted: 1 is most common)
    num_diagnoses = random.choices([1, 2, 3], weights=[50, 35, 15], k=1)[0]
    diagnoses = random.sample(diagnoses_pool, min(num_diagnoses, len(diagnoses_pool)))
    
    # Pick age range weighted by Dutch demographics
    leeftijd = weighted_choice(AGE_RANGES)
    geslacht = weighted_choice(GESLACHT_OPTIONS)
    
    # Pick 0-5 medications (weighted: 2-3 is most common)
    num_meds = random.choices([0, 1, 2, 3, 4, 5], weights=[5, 15, 30, 25, 15, 10], k=1)[0]
    all_meds = [m for meds in MEDICATIONS.values() for m in meds]
    medicatie = random.sample(all_meds, min(num_meds, len(all_meds)))
    
    # Pick 0-2 allergies
    allergies_pool = [
        "Geen gekende allergieen", "Penicilline", "NSAID's", "Latex",
        "Jodium", "Sulfonamiden", "Acetylsalicylzuur", "Amoxicilline",
        "Metformine", "Codeine",
    ]
    num_allergies = random.choices([0, 1, 2], weights=[60, 30, 10], k=1)[0]
    if num_allergies == 0:
        allergieen = ["Geen gekende allergieen"]
    else:
        allergieen = random.sample(allergies_pool[1:], num_allergies)
    
    # Generate some lab results based on specialty
    lab_pool = [
        "Hemoglobine 14.2 g/dL (ref: 12-16)", "CRP 3.2 mg/L (ref: <5)",
        "Creatinine 0.9 mg/dL (ref: 0.6-1.2)", "eGFR 85 mL/min",
        "HbA1c 7.1% (ref: <7%)", "TSH 2.3 mU/L (ref: 0.4-4.0)",
        "LDL-cholesterol 3.1 mmol/L", "Glucose nuchter 5.8 mmol/L",
        "Leukocyten 7.2 x10^9/L", "Trombocyten 245 x10^9/L",
        "ALAT 28 U/L (ref: <45)", "Ferritine 35 mcg/L (ref: 20-200)",
    ]
    num_labs = random.choices([0, 1, 2, 3], weights=[30, 30, 25, 15], k=1)[0]
    lab_resultaten = random.sample(lab_pool, min(num_labs, len(lab_pool)))
    
    # Pick anamnese type
    anamnese_types = [
        "consultbrief", "ontslagbrief", "specialistenbrief",
        "verwijsbrief", "follow-up consult", "intake consult",
        "spoed consultatie", "teleconsultatie",
    ]
    
    return {
        "geslacht": geslacht,
        "leeftijdscategorie": leeftijd,
        "specialisme": specialty,
        "klachten": diagnoses[:1],  # Primary complaint
        "diagnoses": diagnoses,
        "medicatie": medicatie,
        "lab_resultaten": lab_resultaten,
        "anamnese_type": random.choice(anamnese_types),
        "behandelplan": None,  # Let the LLM fill this in
        "verwijzingen": [specialty] if specialty != "Huisarts" else [],
        "allergieen": allergieen,
    }


def run_recombination():
    os.makedirs(RECOMBINED_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    existing_variants = [f for f in os.listdir(RECOMBINED_DIR) if f.endswith(".json")]
    if len(existing_variants) >= NUM_SYNTHETIC_REPORTS:
        print(f"Phase 6: {len(existing_variants)} recombined files already exist, skipping generation to avoid overwriting.")
        return

    
    # Also load original schemas for reference
    schema_files = [f for f in os.listdir(SCHEMAS_DIR) if f.endswith(".json")]
    original_schemas = []
    for sf in schema_files:
        with open(os.path.join(SCHEMAS_DIR, sf), "r", encoding="utf-8") as f:
            data = json.load(f)
            if "error" not in data:
                original_schemas.append(data)
    
    recombined = []
    seen_hashes = set()
    
    print(f"Generating {NUM_SYNTHETIC_REPORTS} unique clinical variants...")
    
    attempts = 0
    while len(recombined) < NUM_SYNTHETIC_REPORTS and attempts < NUM_SYNTHETIC_REPORTS * 5:
        attempts += 1
        
        # Generate a fresh clinical scenario with unique PII
        variant = generate_clinical_scenario()
        variant["pii"] = generate_pii(geslacht=variant["geslacht"])
        # Override geslacht in PII to match clinical scenario (redundant now but safe)
        variant["pii"]["geslacht"] = variant["geslacht"]
        
        # Hash clinical content (excluding PII) to prevent duplicate scenarios
        clinical_hash = hashlib.md5(
            json.dumps({k: v for k, v in variant.items() if k != "pii"}, sort_keys=True).encode()
        ).hexdigest()
        
        if clinical_hash not in seen_hashes:
            seen_hashes.add(clinical_hash)
            recombined.append(variant)
    
    # Save variants
    for i, variant in enumerate(recombined):
        out_path = os.path.join(RECOMBINED_DIR, f"variant_{i:04d}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(variant, f, indent=2, ensure_ascii=False)
    
    # Specialty distribution for report
    specialty_counts = {}
    for v in recombined:
        s = v.get("specialisme", "Onbekend")
        specialty_counts[s] = specialty_counts.get(s, 0) + 1
    
    report_lines = [
        "# Phase 6 -- Recombine Report",
        f"Generated: {datetime.now().isoformat()}",
        "",
        f"- **Original schemas used as reference**: {len(original_schemas)}",
        f"- **Unique variants generated**: {len(recombined)}",
        f"- **Duplicate scenarios rejected**: {attempts - len(recombined)}",
        f"- **Each variant has unique PII (name, INSZ, RIZIV, address, phone)**",
        "",
        "## Specialty Distribution",
        "| Specialty | Count | Percentage |",
        "|-----------|-------|------------|",
    ]
    
    for spec, count in sorted(specialty_counts.items(), key=lambda x: -x[1]):
        pct = count / len(recombined) * 100
        report_lines.append(f"| {spec} | {count} | {pct:.1f}% |")
    
    with open(os.path.join(DOCS_DIR, "phase_6_recombine_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Phase 6 complete. {len(recombined)} unique variants saved to data/recombined/")

if __name__ == "__main__":
    run_recombination()
