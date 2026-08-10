"""
Pushes the already-trained winning model (from
farahelmashad/personal-pii-tamerbert-trial's saved final_model/, mounted
read-only via kernel_sources) straight to a private HF Hub repo.

Deliberately does NOT retrain -- this kernel only loads and pushes, so it
runs in under a minute and costs no GPU quota. The model weights never
touch any local disk outside Kaggle's own infrastructure; the token is
read from a private Kaggle dataset (never printed, never logged).
"""
import os

from huggingface_hub import login
from transformers import AutoModelForTokenClassification, AutoTokenizer

def find_one(name, is_dir=False):
    """Locate `name` anywhere under /kaggle/input -- mount path conventions
    (dataset vs kernel_sources, with/without an owner-name segment) aren't
    worth hardcoding when a short walk settles it definitively."""
    for root, dirs, files in os.walk("/kaggle/input"):
        if is_dir and name in dirs:
            return os.path.join(root, name)
        if not is_dir and name in files:
            return os.path.join(root, name)
    raise FileNotFoundError(f"{name!r} not found anywhere under /kaggle/input")


print("=== /kaggle/input tree ===")
for root, dirs, files in os.walk("/kaggle/input"):
    depth = root.count(os.sep) - "/kaggle/input".count(os.sep)
    if depth > 4:
        continue
    print("  " * depth + root)
    for fn in files:
        print("  " * (depth + 1) + fn)
print("=== end tree ===")

MODEL_DIR = find_one("final_model", is_dir=True)
TOKEN_PATH = find_one("token.txt")
REPO_ID = "farahelmashad/pii-tamerbert-v5"
print(f"resolved MODEL_DIR={MODEL_DIR}  TOKEN_PATH={TOKEN_PATH}")

with open(TOKEN_PATH, encoding="utf-8") as f:
    token = f.read().strip()

login(token=token)

model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

model.push_to_hub(REPO_ID, private=True)
tokenizer.push_to_hub(REPO_ID, private=True)

print(f"DONE: pushed to https://huggingface.co/{REPO_ID} (private)")
