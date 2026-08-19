# How the Dutch fine-tune was actually run on Kaggle — and how to raise the bar for French/English

Companion to `DUTCH_FINETUNING_HISTORY.md` (the trial-by-trial evidence log)
and `english/HANDOFF.md` (the French chronology + English open questions).
Those documents cover *what happened and why*; this one covers *the
mechanics of how it was actually executed* — the Kaggle kernel structure,
the training script itself, and the practice of always pulling raw results
rather than trusting a remembered number. It ends with concrete additions
to make French/English's evaluation more rigorous than Dutch's was.

Everything below is read directly from the real files
(`personal_finetune/kaggle_final_push/train_and_eval.py` and the
`kernel-metadata.json` in `kaggle_tamerbert_trial/`, `kaggle_discovery_eval/`,
`kaggle_quantize/`), not reconstructed from memory.

---

## 1. What a "kernel" is in this project

Every trial is a **Kaggle script kernel**: one Python file plus a
`kernel-metadata.json` that fully declares its inputs. Four distinct kernel
*roles* were used, and they compose via two mount mechanisms:

- **`dataset_sources`** — mounts a Kaggle dataset (input data, or a private
  dataset holding a secret like an HF token) at
  `/kaggle/input/datasets/<owner>/<dataset-slug>/`.
- **`kernel_sources`** — mounts *another kernel's saved output* at
  `/kaggle/input/notebooks/<owner>/<kernel-slug>/` (not the naive
  `/kaggle/input/<slug>/` path — this is easy to get wrong).

| Kernel | Role | `dataset_sources` | `kernel_sources` | GPU |
|---|---|---|---|---|
| `personal-pii-tamerbert-trial` | train + eval | the synthetic training data | **itself** (see §2) | Tesla T4 |
| `personal-pii-discovery-eval` | inference-only re-eval | same training data (for eval docs) | the trial kernel | Tesla T4 |
| `personal-pii-quantize-eval` | INT8 export + eval | training data + a private dataset holding the HF token | none | CPU only |
| `personal-pii-push-to-hf` | push final model | none | the trial kernel's saved model | CPU only |

## 2. The resume-from-checkpoint pattern — why `run2`→`run9` are one continued line, not 9 separate experiments

`kaggle_tamerbert_trial/kernel-metadata.json` lists its **own kernel id**
inside its own `kernel_sources`. That's deliberate: on each re-run, the
kernel mounts its *previous version's* saved output, and the script does

```python
last_checkpoint = get_last_checkpoint(OUTPUT_DIR) if os.path.isdir(OUTPUT_DIR) else None
trainer.train(resume_from_checkpoint=last_checkpoint)
```

So `run2` through `run9` are **one continued training/config-tweak
sequence**, not nine from-scratch retrains — which is exactly why their
indist F1 numbers cluster so tightly (0.9857–0.9866, §3 of
`DUTCH_FINETUNING_HISTORY.md`): each step is a small perturbation on the
last (a regex fix, an augmentation batch added, a seed check), not a new
experiment starting from zero. **For French/English, decide explicitly
whether a given change warrants continuing this chain (small tweak) or
starting a fresh kernel (a real architectural change, e.g. a different base
model) — conflating the two makes the trial history much harder to read
later, the way it briefly was here.**

`discovery_eval` uses the *same* mount mechanism but points at the trial
kernel instead of itself, and sets `SKIP_TRAINING=1` so `trainer.train()`
never runs at all — it exists purely to re-run inference and eval against
a new stress-test file without spending GPU quota on a retrain. Use this
pattern liberally: **before spending GPU time on a new training run, check
whether the question can be answered by re-evaluating an existing
checkpoint against new eval data instead.**

## 3. The training script itself — what actually happens, in order

Reading `train_and_eval.py` top to bottom:

1. **Self-contained by necessity**: Kaggle script kernels don't reliably put
   sibling `.py` files on `sys.path`, so `dutch_regex.py`, the data-loading
   logic, and the eval-metrics code are all inlined into one file rather
   than imported. **Keep this pattern for French/English** — don't assume
   a multi-file layout will just work on Kaggle.
2. **Data loading & dedup**: loads from up to 4 different provenances
   (`batch_final`, `labeled`/Presidio-style, `hf`, `legacy`), each with its
   own label-name mapping table, resolves address granularity
   (`ADDRESS_MODE=single|decomposed`), computes a `group_key` per record
   and deduplicates by `SOURCE_PRIORITY` so the same underlying document
   appearing in two sources doesn't get counted twice.
3. **Tokenization**: `AutoTokenizer.from_pretrained(MODEL_HF_ID, add_prefix_space=True)`
   — `add_prefix_space=True` matters for RoBERTa-family tokenizers and must
   carry over to whatever French/English base model is chosen if it's also
   RoBERTa-family. Sliding window via `stride=128`, `max_length=512`,
   `return_overflowing_tokens=True` — each document can produce multiple
   training windows, tracked via `overflow_to_sample_mapping`.
4. **Label alignment**: builds a **character-level BIO array** for the
   whole document first (`char_bio()`), then looks up each token's label
   through its offset mapping — this is what makes label alignment robust
   to tokenizer quirks, rather than trying to align labels token-by-token
   during tokenization directly. Special tokens get `-100` (ignored by the
   loss).
5. **Training**: `TrainingArguments(learning_rate=2e-5, per_device_train_batch_size=16, max_steps=1500, save_steps=250, fp16=<gpu available>)`.
   `max_steps` (not epochs) is the control knob, overridable via the
   `MAX_STEPS` env var — this is how the final push extended training
   further under deadline pressure without restructuring the script.
   `save_total_limit` is deliberately sized to **keep every checkpoint**
   (not just the last 2), specifically so the next step can build a full
   overfitting curve.
6. **Decoding**: greedy BIO-to-span decoding per sliding window
   (`decode_model_preds`), spans from overlapping windows resolved via
   longest-span-wins (`resolve_overlaps`).
7. **Three eval surfaces, in two matching modes, every single run** —
   `model_only`, `regex_only`, `full_pipeline`, each scored both `strict`
   (exact span match) and `relaxed` (any overlap counts) — six full reports
   per run, not one. This is a real rigor axis `DUTCH_FINETUNING_HISTORY.md`
   didn't call out explicitly: **strict vs. relaxed matching is computed by
   default for every trial**, not added later.
8. **Bootstrap 95% confidence intervals**, per label, computed automatically
   for every report (1000 resamples) — also already standard practice, not
   something to add.
9. **Confusion matrices** (gold label → predicted label, top 10
   non-diagonal pairs) — printed for every report, showing exactly which
   labels get confused for which.
10. **Post-hoc checkpoint-curve overfitting check**: after training, every
    saved `checkpoint-*` directory is *individually reloaded* and
    re-evaluated — not just the final checkpoint — producing the step-by-step
    curve quoted in `DUTCH_FINETUNING_HISTORY.md` §3. This is how "no
    overfitting, plateaus by step 1500" was actually established, not
    asserted.
11. **`raw_predictions.json` is saved deliberately** so that "regex-ownership
    / merge-strategy ablation can be re-run post-hoc, locally, against these
    cached predictions — without spending another GPU trial to retrain the
    model" (the script's own comment). This is *the* concrete mechanism
    behind §3's "cheap discovery before expensive retrain" principle.
12. **Cleanup and push**: the HF token is read from an environment variable
    only — never hardcoded (an earlier version did, and that token had to
    be revoked after GitHub's push protection caught it, see
    `feedback_kaggle_workflow_gotchas` memory). After an optional push to a
    **private** HF repo, `shutil.rmtree(OUTPUT_DIR)` runs unconditionally —
    **a full model checkpoint must never end up in the Kaggle kernel's
    Output bundle**, only the small JSON reports do. This is stricter than
    "don't let it touch the laptop" — it doesn't even survive in Kaggle's
    own output storage.

## 4. "We pulled the results directly" — make this a standing practice, not a one-off

Every number that ended up in `DUTCH_FINETUNING_HISTORY.md`, in the
executive-summary slides, and in this document was obtained the same way:
`kaggle kernels output <kernel> --file-pattern "reports/.*"` to download
just the small JSON reports (never the model weights — `--file-pattern` is
a *regex*, not a glob, and omitting it once nearly downloaded ~500MB of
checkpoint by accident), then reading the raw `eval_report.json`/
`checkpoint_curve.json` file directly rather than trusting a paraphrased
or remembered number.

**Concretely, twice in this project a remembered/summarized number turned
out to need correction once the raw file was actually read**: the
executive-summary slides were rebuilt after the underlying PDF was
re-checked, and this history document itself only exists because the raw
`eval_report.json` files, not the `project_tamerbert_winning_model` memory
summary, were what got read to build it. **Apply this as a rule for
French/English too: before citing any F1 number in a write-up, a Slack
message, or a memory file, pull the actual `reports/eval_report.json` for
that specific run and read it — don't propagate a number from an earlier
summary, including this document, without re-verifying it against the
source file if the claim matters.**

## 5. Making French/English's evaluation more rigorous than Dutch's

The Dutch pipeline's eval was already meaningfully rigorous (§3, items 7–11
above) — strict/relaxed matching, bootstrap CIs, confusion matrices, and a
full per-checkpoint overfitting curve were standard on every run, not
bolted on later. Real gaps worth closing for French/English, each
concrete and buildable on data the generator already produces:

1. **Paired significance testing between runs, not just per-run CIs.**
   Every run reports its own bootstrap CI, but nothing tests whether
   `run8_augmented`'s 0.9866 is *significantly* different from `run7`'s
   0.9857, or within noise. Add a paired bootstrap or McNemar's test on the
   same eval set across two checkpoints before claiming an improvement is
   real.
2. **Score the fairness slice the generator already collects, but which
   nothing currently reads at eval time.** `pii_table.py`'s own docstring
   states `name_origin` "exists to measure DIFFERENTIAL RECALL: a model
   trained only on Flemish names under-detects Maghrebi, Turkish, Slavic
   and Central African names" — a real, explicit design intent. Nothing in
   `train_and_eval.py`'s eval path actually slices recall by `name_origin`.
   **This is a genuine, currently-unrealized gap, not a hypothetical
   addition** — the metadata already exists in every generated `Case`; wire
   it into the eval report as a per-origin recall breakdown for NAME (and
   for French/English, extend it to whatever origin categories that
   language's generator uses).
3. **Score per-format-variant recall, not just per-label.** `pii_table.py`
   records the exact surface-format variant sampled for every field
   (`case.fmt` — which of ~14 date formats, which phone-format variant,
   etc.) but this is discarded before eval; only the label-level aggregate
   is scored. A label can look fine in aggregate while one specific rare
   format variant is silently much worse — slice recall by `fmt` value
   (already computed in `audit()`'s "format variant coverage" section, just
   never carried through to the *eval* report) to catch this.
4. **Report confidence-interval width as an explicit caveat on small
   surfaces**, not just the interval itself. The `real` surface has n=5
   documents and `ood` has n=14 — CIs on surfaces this small are
   necessarily wide, and a single-digit-document eval set can't reliably
   detect anything but a large effect. State the achievable statistical
   power explicitly (e.g. "with n=14, this eval can't distinguish F1 0.80
   from F1 0.85") rather than reporting a point estimate that implies more
   precision than the sample size supports.
5. **Boundary-error distance, not just strict/relaxed as a binary.**
   `relaxed` mode already tells you *whether* an overlap happened; it
   doesn't tell you *how far off* a boundary miss was. A histogram of
   start/end offset error for near-miss spans would distinguish "off by one
   character" (probably a tokenization/whitespace edge case) from "off by
   twenty characters" (probably a real extraction failure) — currently
   these look identical in a strict-mode failure.
6. **A learning-curve check before finalizing corpus size.** Nothing in
   the Dutch history checks how much training data was actually necessary
   — train on 25%/50%/75%/100% of the final corpus and compare eval curves,
   so French/English's synthetic-data investment (currently sized by
   analogy to Dutch's ~6,469 / French's ~11,665 documents, not by a
   data-scaling experiment) has actual evidence behind the number chosen.

Items 2 and 3 are the highest-value additions: both use metadata the
generator *already computes and discards*, so they're a scoring-code change
only, not a new data-generation effort — the cheapest possible way to add
real rigor.

## 6. Kaggle safety practices (cross-reference, not repeated in full)

Already documented in the `feedback_kaggle_workflow_gotchas` memory and
`english/HANDOFF.md`'s intro — apply unchanged to French/English:
`--file-pattern` (regex, not glob) on every `kaggle kernels output` call;
route around the D: drive's real hardware fault via system Python + a
Temp-directory download target; personal HF token read from an environment
variable sourced from a **private** mounted Kaggle dataset, never
hardcoded; `git push` handed to the user, never retried by the agent.
