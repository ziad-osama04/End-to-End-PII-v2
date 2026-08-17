"""Minimal runnable example for pii_pipeline.py.

    pip install -r requirements.txt
    python example_usage.py

Verified working against the actual model (see the smoke-test run this
was built from). Swap SAMPLE_TEXT for a real document to try it out, or
call detect_pii() directly from your own service code -- this file exists
to sanity-check your environment reproduces the same result before wiring
the pipeline into anything real.
"""
from transformers import AutoModelForTokenClassification, AutoTokenizer

from pii_pipeline import detect_pii

REPO_ID = "farahelmashad/pii-medroberta-nl-v2"  # public on HF Hub

SAMPLE_TEXT = (
    "Patient: Jan Janssens, geboren 12-05-1980, 44 jaar. "
    "Adres: Kerkstraat 12, 9000 Gent. Tel 0475123456. "
    "INSZ 71030410130."
)

EXPECTED = [
    ("NAME", "Jan Janssens"),
    ("DATE", "12-05-1980"),
    ("AGE", "44"),
    ("ADDRESS", "Kerkstraat 12, 9000 Gent"),
    ("PHONE", "0475123456"),
    ("INSZ", "71030410130"),
]


def main():
    print(f"Loading {REPO_ID} ...")
    model = AutoModelForTokenClassification.from_pretrained(REPO_ID)
    tokenizer = AutoTokenizer.from_pretrained(REPO_ID, add_prefix_space=True)
    model.eval()

    spans = detect_pii(SAMPLE_TEXT, model, tokenizer)

    print(f"\nInput:  {SAMPLE_TEXT!r}\n")
    print("Detected spans:")
    for s in spans:
        print(f"  {s['label']:14s} {SAMPLE_TEXT[s['start']:s['end']]!r}")

    got = {(s["label"], SAMPLE_TEXT[s["start"]:s["end"]]) for s in spans}
    missing = set(EXPECTED) - got
    if missing:
        print(f"\nWARNING: expected spans not found: {missing}")
        print("Your environment may differ from the one this was verified against"
              " (see requirements.txt) -- check transformers/torch versions.")
    else:
        print("\nOK -- matches the expected result for this sample.")


if __name__ == "__main__":
    main()
