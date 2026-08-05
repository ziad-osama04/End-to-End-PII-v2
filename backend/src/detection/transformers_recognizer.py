"""
Custom Presidio recognizer that wraps the fine-tuned MedRoBERTa.nl PII model.

By default it loads the model from the Hugging Face Hub repo
`ziadosama/final-pii-model-v2` (the v2 taxonomy: NAME, DATE, ORGANIZATION, CITY,
ZIP_CODE, STREET, BUILDING_NUMBER, AGE, PHONE, INSZ, RIZIV, URL, EMAIL). Set
PII_MODEL_DIR to a local folder path to load it from disk instead (e.g. offline).
The recognizer reads the label set from the model config, so no label list is
hardcoded here.

The model source can be either a Hub repo id or a local directory — both are
handled transparently via `from_pretrained`. For a PRIVATE Hub repo you must be
authenticated: run `huggingface-cli login` once, or set the HF_TOKEN env var.
"""
import os

from presidio_analyzer import EntityRecognizer, RecognizerResult

# --- Model source: Hub repo id by default; override with PII_MODEL_DIR --------
DEFAULT_MODEL = "ziadosama/final-pii-model-v2"
MODEL_SOURCE = os.environ.get("PII_MODEL_DIR", DEFAULT_MODEL)

# Token for private repos (falls back to a cached `huggingface-cli login`)
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

# Detection confidence floor and long-text chunking.
# The model (RoBERTa) accepts at most 512 tokens. We window by *tokens*, not
# characters, because dense tabular text (e.g. spirometry tables with spaced-out
# single characters) tokenizes into far more tokens per character than prose and
# would otherwise overflow the 512-token position buffer and crash the model.
SCORE_THRESHOLD = float(os.environ.get("PII_SCORE_THRESHOLD", "0.5"))
_MAX_TOKENS = 400      # window size in model tokens (< 512, leaving room for specials)
_TOKEN_OVERLAP = 50    # token overlap between consecutive windows


class MedRobertaPIIRecognizer(EntityRecognizer):
    def __init__(self, model_source: str = MODEL_SOURCE, score_threshold: float = SCORE_THRESHOLD):
        self.model_source = model_source
        self.score_threshold = score_threshold
        self._pipe = None  # lazy-loaded on first analyze()

        # Read the label set from the model config (works for a Hub id OR a
        # local path). Strip BIO prefixes to get the canonical entity types.
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(model_source, token=HF_TOKEN)
        id2label = config.id2label
        entities = sorted({lab.split("-", 1)[1] for lab in id2label.values() if lab != "O"})
        self._model_entities = entities

        super().__init__(
            supported_entities=entities,
            supported_language="nl",
            name="MedRobertaPIIRecognizer",
        )

    def load(self) -> None:  # required by EntityRecognizer, nothing to eager-load
        pass

    def _ensure_pipe(self):
        if self._pipe is None:
            import torch
            from transformers import (AutoTokenizer, AutoModelForTokenClassification,
                                      pipeline)
            tok = AutoTokenizer.from_pretrained(self.model_source, token=HF_TOKEN)
            model = AutoModelForTokenClassification.from_pretrained(
                self.model_source, token=HF_TOKEN
            )
            self._pipe = pipeline(
                "token-classification",
                model=model,
                tokenizer=tok,
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1,
            )
        return self._pipe

    def _windows(self, text: str, tokenizer):
        # Window over model tokens (not characters) so no chunk exceeds the
        # 512-token model limit, regardless of how dense the text tokenizes.
        enc = tokenizer(
            text,
            return_offsets_mapping=True,
            add_special_tokens=False,
            truncation=False,
        )
        offsets = enc["offset_mapping"]
        n = len(offsets)
        if n <= _MAX_TOKENS:
            yield 0, text
            return
        i = 0
        while i < n:
            j = min(n, i + _MAX_TOKENS)
            start_char = offsets[i][0]
            end_char = offsets[j - 1][1]
            yield start_char, text[start_char:end_char]
            if j == n:
                break
            i = j - _TOKEN_OVERLAP

    def analyze(self, text, entities, nlp_artifacts=None):
        if not text or not text.strip():
            return []
        pipe = self._ensure_pipe()
        wanted = set(entities) if entities else None

        results, seen = [], set()
        for offset, chunk in self._windows(text, pipe.tokenizer):
            for ent in pipe(chunk):
                etype = ent["entity_group"]
                if etype not in self._model_entities:
                    continue
                if wanted is not None and etype not in wanted:
                    continue
                score = float(ent["score"])
                if score < self.score_threshold:
                    continue
                start = offset + int(ent["start"])
                end = offset + int(ent["end"])
                key = (start, end, etype)
                if key in seen:
                    continue
                seen.add(key)
                results.append(RecognizerResult(etype, start, end, score))
        return results
