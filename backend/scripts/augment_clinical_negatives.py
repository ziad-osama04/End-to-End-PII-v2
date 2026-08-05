"""Generate clinical-table NEGATIVE examples for the PII fine-tune.

The model used to over-mask the spirometry/lab tables in reports like NOVA3
(tagging values such as ``FEV1`` or ``6.77`` as identifiers). This script writes
synthetic reports that pair a normal PII header with a randomised spirometry /
lung-function / vitals table, and ground-truth spans that cover ONLY the header
PII. Every number inside the table is therefore labelled ``O``, teaching the
model that clinical tables are not PII.

Output is written in ``batch_final`` format so the fine-tune notebook picks it up
as its highest-priority source:

    synthetic_reports/batch_final/reports/synth_neg_XXXXX.txt
    synthetic_reports/batch_final/ground_truth/synth_neg_XXXXX.json

Ground-truth categories match ``MAP_BATCH_FINAL`` in generate_notebook.py, so the
negatives also reinforce the v2 taxonomy (NAME / ORGANIZATION / CITY / ZIP_CODE /
STREET / BUILDING_NUMBER / PHONE / INSZ / RIZIV / DATE).

Usage:
    python backend/scripts/augment_clinical_negatives.py --n 150
Then re-zip synthetic_reports/ for Kaggle.
"""
from __future__ import annotations

import argparse
import json
import os
import random

from faker import Faker

fake = Faker("nl_NL")

HOSPITALS = ["AZORG", "AZ Diest", "UZ Leuven", "AZ Sint-Jan", "AZ Groeninge", "ZOL Genk"]
SPECIALTIES = ["Pneumologie", "Cardiologie", "Gastro-enterologie", "Nefrologie"]
STREET_SUFFIX = ["straat", "laan", "weg", "plein", "steenweg", "lei", "kaai", "markt"]


def _insz() -> str:
    return (f"{random.randint(10,99)}.{random.randint(1,12):02d}.{random.randint(1,28):02d}"
            f"-{random.randint(100,999)}.{random.randint(10,99)}")


def _riziv() -> str:
    return f"{random.randint(1,9)}-{random.randint(10000,99999)}-{random.randint(10,99)}-{random.randint(100,999)}"


def _phone() -> str:
    return f"+32 {random.randint(1,9)} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"


def _spirometry_table() -> str:
    """Return a randomised spirometry + vitals block. All numbers are clinical."""
    def row(label, unit):
        vals = "  ".join(f"{random.uniform(0.3, 8.0):.2f}" for _ in range(3))
        pct = f"{random.randint(30, 130)}"
        z = f"{random.uniform(-2.0, 2.0):.2f}"
        return f"{label:16s} ({unit})  {vals}  {pct}  {z}"

    lines = [
        "SPIROMETRIE       Pre-Broncho        Ventolin",
        "MET BRONCHOD.     Pred.  Meas.  %Pred.  zScore",
        "------------------------------------------------",
        row("FVC", "L"), row("FEV1", "L"), row("FEV1/FVC", "%"),
        row("PEF", "L/sec"), row("FEF 25%", "L/sec"), row("FEF 50%", "L/sec"),
        row("FEF 75%", "L/sec"),
        "",
        "LONGV. PLETHYSMOGR.  Pred.   Meas.  %Pred.  zScore",
        row("VC", "L"), row("RV (Pleth)", "L"), row("TLC (Pleth)", "L"),
        "",
        "OPMERKING TECHNICUS",
        "-------------------",
        f"spo2: {random.randint(88, 99)}%",
        f"BD: {random.randint(100,160)}/{random.randint(60,95)} HR: {random.randint(55,95)}",
        f"GESTALTE: {random.randint(150,195)}.0 cm   GEWICHT: {random.randint(50,110)}.0 kg   "
        f"BMI: {random.uniform(18,32):.2f}",
        f"LEEFTIJD: {random.randint(30,90)} jaar   RAS: caucasisch",
    ]
    return "\n".join(lines)


def make_report():
    """Return (text, entities) with entities covering ONLY the header PII."""
    ents = []
    parts = []
    cursor = [0]

    def add(s):
        parts.append(s)
        cursor[0] += len(s)

    def add_pii(value, category):
        start = cursor[0]
        add(value)
        ents.append({"category": category, "value": value,
                     "spans": [[start, start + len(value)]]})

    hospital = random.choice(HOSPITALS)
    specialty = random.choice(SPECIALTIES)
    patient = fake.name()
    doctor = "dr. " + fake.last_name()
    street = fake.last_name() + random.choice(STREET_SUFFIX)
    house = str(random.randint(1, 250))
    zipc = str(random.randint(1000, 9999))
    city = fake.city()
    date = fake.date_this_year().strftime("%d/%m/%Y")

    add("BRIEF\n\nPATIENT: ")
    add_pii(patient, "patient_full_name")
    add("\nINSZ: ")
    add_pii(_insz(), "patient_national_register_number")
    add("\nVERZONDEN DOOR ")
    add_pii(doctor, "referring_doctor_name")
    add("\nDATUM: ")
    add_pii(date, "report_date")
    add("\n\n")
    add_pii(hospital, "hospital_name")
    add("\n" + specialty + "\n\n")   # specialty intentionally NOT a PII span
    add("Geachte collega,\n\n")
    add(_spirometry_table())
    add("\n\n---------------------------------------------\n")
    # institution footer address, split into components
    add_pii(street, "institution_street_name")
    add(" ")
    add_pii(house, "institution_house_number")
    add(", ")
    add_pii(zipc, "institution_postal_code")
    add(" ")
    add_pii(city, "institution_city")
    add("   ")
    add_pii(_phone(), "institution_phone")
    add("\nhttps://www.azorg.be\n")

    return "".join(parts), ents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    # Training data now lives under training/synthetic_reports (fall back to a
    # top-level synthetic_reports if that layout isn't present).
    train_sr = os.path.join(project_root, "training", "synthetic_reports")
    base_sr = train_sr if os.path.isdir(train_sr) else os.path.join(project_root, "synthetic_reports")
    bf = os.path.join(base_sr, "batch_final")
    rep_dir = os.path.join(bf, "reports")
    gt_dir = os.path.join(bf, "ground_truth")
    os.makedirs(rep_dir, exist_ok=True)
    os.makedirs(gt_dir, exist_ok=True)

    for i in range(args.n):
        doc_id = f"synth_neg_{i:05d}"
        text, ents = make_report()
        with open(os.path.join(rep_dir, doc_id + ".txt"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(gt_dir, doc_id + ".json"), "w", encoding="utf-8") as f:
            json.dump({"doc_id": doc_id, "language": "nl", "pii_entities": ents},
                      f, ensure_ascii=False, indent=1)

    print(f"Wrote {args.n} clinical-negative reports to {rep_dir}")
    print("Re-zip synthetic_reports/ before uploading to Kaggle.")


if __name__ == "__main__":
    main()
