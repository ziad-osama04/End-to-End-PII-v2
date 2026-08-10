"""Dependency-light runtime for the INT8 ONNX PII model.

Runs ``farahelmashad/pii-medroberta-nl-v2-int8-onnx`` with onnxruntime + the
Hugging Face fast tokenizer only -- no ``optimum``, no ``torch``. This mirrors
how a lean production container would serve the quantized model.

The model is a RoBERTa (MedRoBERTa.nl) token classifier with a BIO taxonomy over
six entity types: NAME, ADDRESS, ORGANIZATION, DATE, AGE, PHONE. Structured
identifiers (EMAIL, IBAN, INSZ, RIZIV, ...) are intentionally NOT model labels;
they are covered by the Dutch regex layer elsewhere in the pipeline.

Model source resolution:
    * ``PII_ONNX_MODEL_DIR`` env var -> load from that local directory (offline);
    * otherwise download the Hub repo ``DEFAULT_REPO`` on first use.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import numpy as np

DEFAULT_REPO = "farahelmashad/pii-medroberta-nl-v2-int8-onnx"

# The six entity types the model was fine-tuned to detect.
EXPECTED_ENTITY_TYPES = frozenset(
    {"NAME", "ADDRESS", "ORGANIZATION", "DATE", "AGE", "PHONE"}
)


@dataclass(frozen=True)
class Entity:
    """One detected span: character offsets into the input text, plus a label."""

    start: int
    end: int
    label: str
    score: float
    text: str


def resolve_model_dir(repo: str = DEFAULT_REPO) -> str:
    """Return a local directory holding the ONNX model + tokenizer + config.

    Uses ``PII_ONNX_MODEL_DIR`` when it points at a real directory; otherwise
    downloads a snapshot of *repo* from the Hub.
    """
    local = os.environ.get("PII_ONNX_MODEL_DIR")
    if local and os.path.isdir(local):
        return local
    from huggingface_hub import snapshot_download

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return snapshot_download(repo, token=token)


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=-1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=-1, keepdims=True)


class OnnxPiiDetector:
    """Load the INT8 ONNX model once and detect PII spans in Dutch text."""

    def __init__(
        self,
        model_dir: str | None = None,
        *,
        threshold: float = 0.5,
        max_length: int = 512,
        stride: int = 64,
        providers: list[str] | None = None,
    ) -> None:
        import onnxruntime as ort
        from transformers import AutoTokenizer

        self.model_dir = model_dir or resolve_model_dir()
        self.threshold = threshold
        self.max_length = max_length
        self.stride = stride

        with open(os.path.join(self.model_dir, "config.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        self.config = config
        self.id2label = {int(k): v for k, v in config["id2label"].items()}
        self.num_labels = len(self.id2label)
        self.entity_types = frozenset(
            label.split("-", 1)[1] for label in self.id2label.values() if label != "O"
        )

        self.session = ort.InferenceSession(
            os.path.join(self.model_dir, "model.onnx"),
            providers=providers or ["CPUExecutionProvider"],
        )
        self.input_names = [i.name for i in self.session.get_inputs()]
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)

    # -- low level ---------------------------------------------------------- #
    def logits(self, text: str) -> np.ndarray:
        """Return raw ``[seq, num_labels]`` logits for a single truncated window.

        Exposed for tests that need to assert on shapes and determinism.
        """
        enc = self.tokenizer(
            text,
            return_tensors="np",
            truncation=True,
            max_length=self.max_length,
        )
        feed = {name: enc[name].astype(np.int64) for name in self.input_names}
        return self.session.run(None, feed)[0][0]

    # -- BIO aggregation ---------------------------------------------------- #
    def _aggregate(self, logits, offsets, special, text, threshold):
        probs = _softmax(logits)
        ids = probs.argmax(axis=-1)
        scores = probs.max(axis=-1)

        spans: list[dict] = []
        current: dict | None = None
        for idx in range(len(ids)):
            if special[idx] == 1:
                if current:
                    spans.append(current)
                    current = None
                continue
            start, end = int(offsets[idx][0]), int(offsets[idx][1])
            label = self.id2label[int(ids[idx])]
            if label == "O" or end <= start:
                if current:
                    spans.append(current)
                    current = None
                continue
            prefix, etype = (label.split("-", 1) if "-" in label else ("B", label))
            if current and current["type"] == etype and prefix != "B":
                current["end"] = end
                current["scores"].append(float(scores[idx]))
            else:
                if current:
                    spans.append(current)
                current = {
                    "start": start,
                    "end": end,
                    "type": etype,
                    "scores": [float(scores[idx])],
                }
        if current:
            spans.append(current)

        out: list[Entity] = []
        for span in spans:
            avg = sum(span["scores"]) / len(span["scores"])
            if avg >= threshold:
                out.append(
                    Entity(
                        span["start"],
                        span["end"],
                        span["type"],
                        avg,
                        text[span["start"] : span["end"]],
                    )
                )
        return out

    @staticmethod
    def _drop_contained(entities: list[Entity]) -> list[Entity]:
        """Remove a span fully covered by another span of the same label.

        Overlapping windows can each emit part of a boundary entity; the wider
        span from the neighbouring window supersedes the partial one.
        """
        kept: list[Entity] = []
        for ent in sorted(entities, key=lambda e: (e.end - e.start), reverse=True):
            if any(
                other.label == ent.label
                and other.start <= ent.start
                and ent.end <= other.end
                and (other.start, other.end) != (ent.start, ent.end)
                for other in kept
            ):
                continue
            kept.append(ent)
        return kept

    # -- public API --------------------------------------------------------- #
    def detect(self, text: str, threshold: float | None = None) -> list[Entity]:
        """Return PII spans (character offsets into *text*) at or above threshold.

        Long inputs are split into overlapping token windows by the tokenizer;
        spans from every window are merged and de-duplicated.
        """
        if not text or not text.strip():
            return []
        thr = self.threshold if threshold is None else threshold

        enc = self.tokenizer(
            text,
            max_length=self.max_length,
            stride=self.stride,
            truncation=True,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
            return_special_tokens_mask=True,
            padding=True,
            return_tensors="np",
        )
        feed = {name: enc[name].astype(np.int64) for name in self.input_names}
        logits = self.session.run(None, feed)[0]  # [windows, seq, num_labels]

        by_key: dict[tuple[int, int, str], Entity] = {}
        for window in range(logits.shape[0]):
            for ent in self._aggregate(
                logits[window],
                enc["offset_mapping"][window],
                enc["special_tokens_mask"][window],
                text,
                thr,
            ):
                key = (ent.start, ent.end, ent.label)
                if key not in by_key or ent.score > by_key[key].score:
                    by_key[key] = ent

        merged = self._drop_contained(list(by_key.values()))
        return sorted(merged, key=lambda e: (e.start, e.end, e.label))

    def detected_types(self, text: str, threshold: float | None = None) -> set[str]:
        """Return just the set of entity labels found in *text*."""
        return {ent.label for ent in self.detect(text, threshold)}
