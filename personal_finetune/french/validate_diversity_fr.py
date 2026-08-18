#!/usr/bin/env python3
"""
validate_diversity_fr.py -- measures whether the dataset is ACTUALLY diverse,
not just superficially varied. Templates can vary PII values while still
teaching the model trivial positional shortcuts ("anything after 'T ' is a
phone number") instead of real context understanding.

Sections:
  1. Lexical diversity: type-token ratio, distinct-1/2/3 (n-gram diversity)
  2. Vocabulary overlap: train vs held-out-template eval (should be high --
     same language/domain) and TEMPLATE SKELETON overlap (should be ~0 --
     proves held-out templates are structurally distinct, not just relabeled)
  3. Positional/contextual diversity per PII label: for each label, how many
     DISTINCT immediate-preceding-context shapes exist, and what fraction of
     occurrences fall into the single most common context (a high share here
     is exactly the "anything after PHONE:" trap)
  4. Structural diversity counts: distinct templates/specialties/letter_types,
     distinct organizations, distinct format variants per identifier type
"""
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+|\d+")


def tokenize(text):
    return WORD_RE.findall(text.lower())


def ttr(tokens):
    return len(set(tokens)) / len(tokens) if tokens else 0.0


def distinct_n(tokens, n):
    if len(tokens) < n:
        return 0.0
    grams = [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
    return len(set(grams)) / len(grams)


def load_jsonl(path):
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            docs.append(json.loads(line))
    return docs


def mask_template_skeleton(text, spans):
    """Replace every scored span with a generic placeholder, so what's left
    is pure template prose -- used to measure REAL structural overlap."""
    out = text
    for s in sorted(spans, key=lambda s: s["start"], reverse=True):
        out = out[:s["start"]] + f"<{s['label']}>" + out[s["end"]:]
    return out


def section1_lexical(train_docs):
    print("=" * 90)
    print("1. LEXICAL DIVERSITY (train_fr.jsonl, full corpus)")
    print("=" * 90)
    all_tokens = []
    for d in train_docs:
        all_tokens.extend(tokenize(d["text"]))
    print(f"  total tokens: {len(all_tokens):,}")
    print(f"  type-token ratio (whole corpus): {ttr(all_tokens):.4f}  "
          f"(low is expected at corpus scale -- compare to per-doc TTR below)")

    per_doc_ttr = [ttr(tokenize(d["text"])) for d in train_docs[:1000]]
    print(f"  mean per-document TTR (n=1000 docs): {sum(per_doc_ttr)/len(per_doc_ttr):.4f}")

    for n in (1, 2, 3):
        # distinct-n on a sample to keep this fast; still representative
        sample_tokens = []
        for d in train_docs[:1500]:
            sample_tokens.extend(tokenize(d["text"]))
        print(f"  distinct-{n} (n=1500 docs pooled): {distinct_n(sample_tokens, n):.4f}")
    print()


def section2_vocab_overlap(train_docs, heldout_docs):
    print("=" * 90)
    print("2. VOCABULARY OVERLAP: train vs held-out-template eval")
    print("=" * 90)
    train_vocab = set()
    for d in train_docs:
        train_vocab.update(tokenize(d["text"]))
    heldout_vocab = set()
    for d in heldout_docs:
        heldout_vocab.update(tokenize(d["text"]))
    jaccard = len(train_vocab & heldout_vocab) / len(train_vocab | heldout_vocab)
    coverage = len(heldout_vocab & train_vocab) / len(heldout_vocab)
    print(f"  train vocab size: {len(train_vocab):,}   held-out vocab size: {len(heldout_vocab):,}")
    print(f"  Jaccard overlap: {jaccard:.4f}")
    print(f"  held-out word coverage by train vocab: {coverage:.4f}  "
          f"(expect HIGH -- same clinical French language, this is fine and expected)")

    print()
    print("  TEMPLATE SKELETON overlap (PII masked out -- tests structural novelty):")
    train_skel_ngrams = set()
    for d in train_docs[:2000]:
        skel = mask_template_skeleton(d["text"], d["spans"])
        toks = tokenize(skel)
        train_skel_ngrams.update(tuple(toks[i:i + 5]) for i in range(len(toks) - 4))
    heldout_skel_ngrams = set()
    for d in heldout_docs[:2000]:
        skel = mask_template_skeleton(d["text"], d["spans"])
        toks = tokenize(skel)
        heldout_skel_ngrams.update(tuple(toks[i:i + 5]) for i in range(len(toks) - 4))
    skel_overlap = len(train_skel_ngrams & heldout_skel_ngrams) / max(1, len(heldout_skel_ngrams))
    print(f"  held-out 5-gram skeletons also seen in train: {skel_overlap:.4f}  "
          f"(LOW is good -- confirms held-out templates are genuinely distinct prose, "
          f"not just the same sentences with swapped values)")
    print()


def section3_positional_diversity(docs, sample_size=4000):
    print("=" * 90)
    print("3. POSITIONAL/CONTEXTUAL DIVERSITY PER PII LABEL")
    print("=" * 90)
    print("  (checks the exact failure mode described: is a label always in the")
    print("   same syntactic slot, e.g. always right after a fixed word/punctuation?)")
    print()
    contexts_by_label = {}
    for d in docs[:sample_size]:
        text = d["text"]
        for s in d["spans"]:
            label = s["label"]
            before = text[max(0, s["start"] - 20):s["start"]]
            # last 1-3 tokens immediately before the span, punctuation included
            before_shape = before[-12:].strip()
            contexts_by_label.setdefault(label, Counter())[before_shape] += 1

    for label in sorted(contexts_by_label):
        counter = contexts_by_label[label]
        total = sum(counter.values())
        distinct = len(counter)
        top_context, top_count = counter.most_common(1)[0]
        top_share = top_count / total
        flag = " <-- HIGH: check this" if top_share > 0.5 else ""
        print(f"  {label:14s} n={total:6d}  distinct preceding-contexts={distinct:4d}  "
              f"top-context share={top_share:.1%} ({top_context!r}){flag}")
    print()


def section4_structural_counts(train_docs):
    print("=" * 90)
    print("4. STRUCTURAL DIVERSITY COUNTS")
    print("=" * 90)
    templates = set()
    specialties = set()
    letter_types = set()
    orgs = set()
    phone_formats = set()
    date_formats = set()
    for d in train_docs:
        m = d["meta"]
        templates.add(m["template_hash"])
        specialties.add(m["specialty"])
        letter_types.add(m["letter_type"])
        for s in d["spans"]:
            val = d["text"][s["start"]:s["end"]]
            if s["label"] == "ORGANIZATION":
                orgs.add(val)
            elif s["label"] == "PHONE":
                phone_formats.add(re.sub(r"\d", "#", val))
            elif s["label"] == "DATE":
                date_formats.add(re.sub(r"\d", "#", val))
    print(f"  distinct templates: {len(templates)}")
    print(f"  distinct specialties: {len(specialties)}  ->  {sorted(specialties)}")
    print(f"  distinct letter_types: {len(letter_types)}  ->  {sorted(letter_types)}")
    print(f"  distinct organizations (hospitals): {len(orgs)}")
    print(f"  distinct PHONE format shapes (digits collapsed to #): {len(phone_formats)}")
    for fmt in sorted(phone_formats):
        print(f"    {fmt}")
    print(f"  distinct DATE format shapes (digits collapsed to #): {len(date_formats)}")
    for fmt in sorted(date_formats):
        print(f"    {fmt}")
    print()


def main():
    train_docs = load_jsonl("train_fr.jsonl")
    heldout_docs = load_jsonl("tamerbert_data_fr/eval_heldout_templates.jsonl")

    section1_lexical(train_docs)
    section2_vocab_overlap(train_docs, heldout_docs)
    section3_positional_diversity(train_docs)
    section4_structural_counts(train_docs)

    print("=" * 90)
    print("3b. POSITIONAL DIVERSITY ON train_augmented_fr.jsonl (post id_label_variant)")
    print("=" * 90)
    aug_docs = load_jsonl("train_augmented_fr.jsonl")
    section3_positional_diversity(aug_docs)


if __name__ == "__main__":
    main()
