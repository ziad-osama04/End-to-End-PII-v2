"""
perturbation_sweep_en.py -- English port of
personal_finetune/french/perturbation_sweep_fr.py (itself a port of
personal_finetune/ood_stress_test_v2/perturbation_sweep.py).

Applies a battery of cheap, systematic text transforms to documents we
already have correct labels for (a sample of eval_heldout_templates.jsonl +
all eval_real_en.jsonl), each transform correctly recomputing span offsets.
Transform logic ported UNCHANGED -- position/offset mechanics are entirely
language-agnostic, only the source files are English.
"""
import json
import os
import random


def remap_spans_through_edits(text, spans, edits):
    edits = sorted(edits, key=lambda e: e[0])
    out = []
    cum_shift = []
    last = 0
    shift = 0
    for pos, ins in edits:
        out.append(text[last:pos])
        out.append(ins)
        shift += len(ins)
        cum_shift.append((pos, shift))
        last = pos
    out.append(text[last:])
    new_text = "".join(out)

    def remap(offset):
        s = 0
        for pos, cs in cum_shift:
            if pos <= offset:
                s = cs
            else:
                break
        return offset + s

    new_spans = [{"start": remap(sp["start"]), "end": remap(sp["end"]), "label": sp["label"]} for sp in spans]
    return new_text, new_spans


def xf_upper(text, spans):
    return text.upper(), [dict(s) for s in spans]


def xf_lower(text, spans):
    return text.lower(), [dict(s) for s in spans]


def xf_title(text, spans):
    return text.title(), [dict(s) for s in spans]


def xf_whitespace_jitter(text, spans, rng, rate=0.08):
    edits = []
    for i, ch in enumerate(text):
        if ch == " " and rng.random() < rate:
            edits.append((i, " "))
    return remap_spans_through_edits(text, spans, edits)


def xf_strip_trailing_periods(text, spans):
    """Remove the period immediately after any digit run -- directly probes
    the INSZ/RIZIV trailing-punctuation class of bug at scale."""
    out = []
    i = 0
    removed_before = []
    removed = 0
    while i < len(text):
        if text[i] == "." and i > 0 and text[i - 1].isdigit() and (i + 1 == len(text) or text[i + 1] in " \n"):
            removed += 1
            removed_before.append((i, removed))
            i += 1
            continue
        out.append(text[i])
        i += 1
    new_text = "".join(out)

    def remap(offset):
        r = 0
        for pos, cum in removed_before:
            if pos < offset:
                r = cum
            else:
                break
        return offset - r

    new_spans = [{"start": remap(sp["start"]), "end": remap(sp["end"]), "label": sp["label"]} for sp in spans]
    return new_text, new_spans


def xf_nbsp_substitution(text, spans, rng, rate=0.15):
    out = list(text)
    for i, ch in enumerate(out):
        if ch == " " and rng.random() < rate:
            out[i] = " "
    return "".join(out), [dict(s) for s in spans]


def xf_truncate(text, spans, cut_frac):
    cut = int(len(text) * cut_frac)
    new_text = text[:cut]
    new_spans = [dict(s) for s in spans if s["end"] <= cut]
    return new_text, new_spans


TRANSFORMS = {
    "upper": xf_upper,
    "lower": xf_lower,
    "title": xf_title,
    "whitespace_jitter": lambda t, s: xf_whitespace_jitter(t, s, random.Random(1)),
    "strip_trailing_periods": xf_strip_trailing_periods,
    "nbsp_substitution": lambda t, s: xf_nbsp_substitution(t, s, random.Random(2)),
    "truncate_60pct": lambda t, s: xf_truncate(t, s, 0.6),
    "truncate_85pct": lambda t, s: xf_truncate(t, s, 0.85),
}


def sanity_check(doc_id, xf_name, text, spans):
    bad = [sp for sp in spans if not (0 <= sp["start"] < sp["end"] <= len(text))]
    if bad:
        raise AssertionError(f"{doc_id}/{xf_name}: out-of-bounds spans {bad}")


def build_sweep(source_docs, n_sample=40, seed=7):
    rng = random.Random(seed)
    sample = source_docs if len(source_docs) <= n_sample else rng.sample(source_docs, n_sample)
    out = []
    for i, doc in enumerate(sample):
        for xf_name, xf in TRANSFORMS.items():
            new_text, new_spans = xf(doc["text"], doc["spans"])
            sanity_check(f"src{i}", xf_name, new_text, new_spans)
            out.append({
                "id": f"pert_en_{i:03d}_{xf_name}",
                "category": f"perturbation_{xf_name}",
                "note": f"source doc {i}, transform={xf_name}",
                "text": new_text,
                "spans": new_spans,
            })
    return out


if __name__ == "__main__":
    def load(path):
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                out.append({"text": d["text"], "spans": [
                    {"start": s["start"], "end": s["end"], "label": s["label"]} for s in d["spans"]
                ]})
        return out

    HERE = os.path.dirname(__file__)
    heldout = load(os.path.join(HERE, "tamerbert_data_en", "eval_heldout_templates.jsonl"))
    real = load(os.path.join(HERE, "eval_real_en.jsonl"))
    sweep = build_sweep(heldout, n_sample=30) + build_sweep(real, n_sample=len(real))
    print(f"built {len(sweep)} perturbed docs from 30 heldout + {len(real)} real-letter source docs "
          f"x {len(TRANSFORMS)} transforms")

    out_path = os.path.join(HERE, "perturbation_sweep_en.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for d in sweep:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"wrote {out_path}")
