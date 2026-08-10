# Personal fine-tuning track (Farah)

Exploratory PII-NER fine-tuning on `CLTL/MedRoBERTa.nl`, run entirely on
Kaggle kernels (GPU quota, never this laptop). This directory is the code
and small artifacts from that track; pushed here on a branch rather than
`main` so it doesn't collide with in-progress work on `main`.

## Where things actually live

- **Model**: `farahelmashad/pii-medroberta-nl-v2` on HF Hub (also reachable
  as `farahelmashad/pii-tamerbert-v5` -- same weights). This is the final
  checkpoint of this track. Earlier checkpoints (`v1`-`v4`) are kept there
  too for comparison.
- **Full training/eval data**: the Kaggle dataset
  `farahelmashad/personal-pii-tamerbert-generalization-data`. The large
  `train_augmented_v*.jsonl` / `eval_*.jsonl` files are intentionally
  **not** committed here (see `.gitignore`) -- they're regenerated from
  `augmentation/augment_v4.py` over the filtered base data, and committing
  30MB+ JSONL blobs per round into git doesn't buy anything a Kaggle
  dataset doesn't already give us.
- **Quantized (ONNX INT8) model**: `farahelmashad/pii-tamerbert-v5-int8-onnx`
  on HF Hub, built by `kaggle_quantize/quantize_and_eval.py` from the
  `pii-tamerbert-v5` / `pii-medroberta-nl-v2` checkpoint above.

## Layout

- `kaggle_tamerbert_trial/train_and_eval.py` -- the canonical training +
  eval script (current label taxonomy, regex layer, merge logic). Each
  round's script is self-contained (Kaggle script kernels don't reliably
  put sibling `.py` files on `sys.path`), so the regex/eval code below is
  inlined rather than imported.
- `augmentation/augment_v4.py` -- the current (final) augmentation
  pipeline; `augment.py`/`_v2`/`_v3` are kept for history.
- `ood_stress_test*/` -- six rounds of out-of-distribution stress-test
  batteries (`v1` through `v6`), each built fresh with zero content overlap
  with the previous round, used to give an honest generalization verdict
  each retrain.
- `kaggle_discovery_eval/` -- cheap (`SKIP_TRAINING=1`) inference-only
  harness for testing a saved checkpoint against a new eval surface
  without spending GPU quota.
- `kaggle_push_to_hf/` -- pushes a trained checkpoint to HF Hub directly
  from a Kaggle kernel; weights never touch a laptop.
- `kaggle_quantize/` -- ONNX export + dynamic INT8 quantization, with the
  same eval methodology re-run against both fp32 and int8 to confirm size/
  latency gains didn't cost accuracy.

## Regex layer vs. `backend/src/detection/dutch_regex.py`

The regex/validator module inlined in `train_and_eval.py` started as a
direct copy of `backend/src/detection/dutch_regex.py` (see
`kaggle_stage1_trial`'s docstring) but diverged significantly since:

- Adds checksum validators (`valid_insz` with century/bis handling,
  `valid_riziv`, `valid_btw`), a hard-negative filter (`is_hard_negative`,
  rejecting dosing frequencies, blood-pressure ratios, lab-value-adjacent
  numbers), and unicode folding (`fold`) before matching.
- Uses a single merged `ADDRESS` label (model-owned) rather than
  `dutch_regex.py`'s decomposed `ZIP_CODE`/`STREET` -- an early ablation on
  this track's data showed the merged version wins.
- Has no `IBAN` pattern and no gender derivation -- `dutch_regex.py`'s
  `derive_gender()`/`gender_from_insz()` already covers that from a
  detected INSZ, so this track never needed to duplicate it.

These two haven't been reconciled yet. Whoever picks this up next should
decide whether to port the checksum/hard-negative/folding logic into
`dutch_regex.py`, or keep them separate and pick one for the masking
service to actually call.

## Label taxonomy

Model-trained: `NAME`, `DATE`, `PHONE`, `ADDRESS`, `ORGANIZATION`, `AGE`.
Regex-only (never trained): `INSZ`, `RIZIV`, `URL`, `EMAIL`, `BTW_EENHEID`.
`GENDER` is derived downstream from a detected INSZ by
`backend/src/detection/dutch_regex.py` -- not part of this model at all.
