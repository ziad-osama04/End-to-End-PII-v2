# -*- coding: utf-8 -*-
"""Merge the 5 translated_templates_en_batch*.jsonl files into a single
translated_templates_en.jsonl, checking for duplicate hashes and total count."""
import json
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
batch_files = sorted(glob.glob(os.path.join(HERE, "translated_templates_en_batch*.jsonl")))

all_templates = []
seen_hashes = set()
errors = []

for bf in batch_files:
    with open(bf, encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            h = t["template_hash"]
            if h in seen_hashes:
                errors.append(f"DUPLICATE hash {h} (from {os.path.basename(bf)})")
            seen_hashes.add(h)
            all_templates.append(t)

print(f"Merged {len(batch_files)} batch files -> {len(all_templates)} templates")
if errors:
    raise SystemExit("Merge failed:\n" + "\n".join(errors))

out_path = os.path.join(HERE, "translated_templates_en.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for t in all_templates:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

print(f"Wrote {len(all_templates)} templates to {out_path}")
print(f"Unique hashes: {len(seen_hashes)}")
