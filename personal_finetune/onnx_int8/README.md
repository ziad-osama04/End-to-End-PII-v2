# INT8 ONNX PII model — runtime + tests

Validates the quantized deployment artifact
[`farahelmashad/pii-medroberta-nl-v2-int8-onnx`](https://huggingface.co/farahelmashad/pii-medroberta-nl-v2-int8-onnx)
(RoBERTa/MedRoBERTa.nl token classifier, ~126 MB `model.onnx`).

Runs with **onnxruntime + the HF fast tokenizer only** — no `optimum`, no `torch`.

## Files
- `onnx_pii_runtime.py` — `OnnxPiiDetector`: loads `model.onnx` + tokenizer + config,
  softmax + BIO "simple" aggregation, overflow-window handling for long text.
  Reusable outside the tests.
- `test_onnx_int8.py` — the pytest suite.

## Taxonomy
Six entity types (BIO, 13 labels incl. `O`): `NAME, ADDRESS, ORGANIZATION, DATE, AGE, PHONE`.
Structured IDs (EMAIL, IBAN, INSZ, RIZIV, …) are **not** model labels — the Dutch
regex layer covers those.

## Run
```bash
pytest personal_finetune/onnx_int8/test_onnx_int8.py -v
```
The model downloads once from the Hub. For offline/CI, mount the model and set:
```bash
export PII_ONNX_MODEL_DIR=/path/to/model-dir   # holds model.onnx + tokenizer + config.json
```
Optional full-precision parity check (heavy — needs `torch` and the 502 MB model):
```bash
RUN_PARITY=1 pytest personal_finetune/onnx_int8/test_onnx_int8.py -k parity
```

## What is covered
- Packaging: architecture, `id2label` taxonomy, ONNX I/O signature, logits shape.
- Detection: each of the six entity types on realistic Dutch clinical text, plus a
  corpus-wide check that no type is silently lost by quantization.
- Invariants: empty input, determinism, batch-invariance, probability range,
  long-input windowing past the 512-token limit.

Tests **skip** (not fail) when neither `PII_ONNX_MODEL_DIR` nor the Hub is reachable.
