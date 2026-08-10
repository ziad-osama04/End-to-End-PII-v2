"""
Automated perturbation sweep: apply a battery of cheap, systematic text
transforms to documents we already have correct labels for (a sample of
eval_heldout_templates.jsonl + all 5 real docs), each transform correctly
recomputing span offsets. This scales far beyond hand-authoring one example
per idea, and can surface failure modes nobody thought to test for.

Every transform is (text, spans) -> (new_text, new_spans). Two families:
  - length-preserving (casing): spans are untouched, just re-sliced from the
    transformed text.
  - insertion-based (whitespace jitter, punctuation swaps): built via a
    sorted edit list + a monotonic old->new offset remapper, so spans shift
    correctly no matter how many characters get inserted before them.
  - truncation: spans fully inside the kept prefix survive; anything
    straddling or past the cut point is dropped (it should not be
    detectable in a genuinely truncated document, so it isn't gold).
"""
import json
import random


def remap_spans_through_edits(text, spans, edits):
    """edits: list of (position, inserted_text) in the ORIGINAL text's
    coordinate space, sorted by position. Returns (new_text, new_spans)."""
    edits = sorted(edits, key=lambda e: e[0])
    out = []
    cum_shift = []  # (original_position, cumulative_inserted_chars_before_it)
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
    """Randomly double a fraction of single spaces -- a common PDF-extraction
    reflow artifact distinct from the letter-spacing-inside-a-word noise
    already covered in the first OOD battery."""
    edits = []
    for i, ch in enumerate(text):
        if ch == " " and rng.random() < rate:
            edits.append((i, " "))
    return remap_spans_through_edits(text, spans, edits)


def xf_strip_trailing_periods(text, spans):
    """Remove the period immediately after any digit run -- directly probes
    the INSZ/RIZIV trailing-punctuation class of bug at scale, across many
    documents/fields rather than the one instance found by hand."""
    edits = []  # deletions, modeled as negative-length "insert" via rebuild
    out = []
    new_spans_shift = []
    i = 0
    removed_before = []  # (orig_pos, cumulative_removed)
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
    """Swap a fraction of regular spaces for NBSP (U+00A0) -- patterns.py's
    fold() already normalizes this for regex, but the MODEL sees raw text;
    untested whether the tokenizer/model handles it as gracefully."""
    out = list(text)
    for i, ch in enumerate(out):
        if ch == " " and rng.random() < rate:
            out[i] = " "
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
    """source_docs: list of {"text":..., "spans":[{"start","end","label"},...]}
    Returns a list of perturbed docs, one per (sampled source doc x transform)."""
    rng = random.Random(seed)
    sample = source_docs if len(source_docs) <= n_sample else rng.sample(source_docs, n_sample)
    out = []
    for i, doc in enumerate(sample):
        for xf_name, xf in TRANSFORMS.items():
            new_text, new_spans = xf(doc["text"], doc["spans"])
            sanity_check(f"src{i}", xf_name, new_text, new_spans)
            out.append({
                "id": f"pert_{i:03d}_{xf_name}",
                "category": f"perturbation_{xf_name}",
                "note": f"source doc {i}, transform={xf_name}",
                "text": new_text,
                "spans": new_spans,
            })
    return out


if __name__ == "__main__":
    import os
    import sys

    ROOT = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data")

    def load(fname):
        out = []
        with open(os.path.join(ROOT, fname), encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                out.append({"text": d["text"], "spans": [
                    {"start": s["start"], "end": s["end"], "label": s["label"]} for s in d["spans"]
                ]})
        return out

    heldout = load("eval_heldout_templates.jsonl")
    real = load("eval_real.jsonl")
    sweep = build_sweep(heldout, n_sample=30) + build_sweep(real, n_sample=5)
    print(f"built {len(sweep)} perturbed docs from {30} heldout + {5} real source docs "
          f"x {len(TRANSFORMS)} transforms")

    out_path = os.path.join(os.path.dirname(__file__), "perturbation_sweep.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for d in sweep:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"wrote {out_path}")
