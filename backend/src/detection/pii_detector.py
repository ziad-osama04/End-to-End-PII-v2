from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from src.detection.dutch_regex import get_dutch_regex_recognizers
from src.detection.transformers_recognizer import MedRobertaPIIRecognizer

# Entity types the model detects but that we KEEP visible by default (clinical
# content, not identity). Add/remove here to change what gets redacted.
KEEP_VISIBLE = {"CLINICAL_NOTE", "MEDICATION"}

# When the model and the regex both fire on the same text, keep the most specific
# label and drop the overlapping duplicate. Higher number wins. Structured,
# verifiable identifiers outrank generic ones, so a number caught as both PHONE
# and INSZ is masked once, as INSZ.
_LABEL_PRIORITY = {
    "EMAIL": 10, "URL": 10, "IBAN": 9, "INSZ": 9, "RIZIV": 9, "BTW_EENHEID": 9,
    # DATE outranks ZIP/PHONE so a full date (28-05-2026) beats a stray year that
    # the model mislabels ZIP_CODE (2026); the ID labels above still beat DATE.
    "DATE": 8, "PHONE": 7, "ZIP_CODE": 6, "BUILDING_NUMBER": 6, "STREET": 6,
    "CITY": 6, "AGE": 5, "NAME": 4, "ORGANIZATION": 3,
}


def resolve_overlaps(results):
    """Drop only *fully redundant* spans, never reducing masked coverage.

    Spans are considered best-first (label priority, then score, then length). A
    span is kept whenever it covers at least one character not already masked by a
    higher-ranked span; a span whose characters are already fully covered is
    dropped as a duplicate. So a value tagged both PHONE and INSZ collapses to the
    higher-priority INSZ, while a partial overlap keeps both spans rather than
    leave any character exposed.

    Coverage guarantee: the union of characters covered by the kept spans equals
    the union covered by the input, so this can only raise precision (fewer
    duplicate labels) and can never lower recall.
    """
    def rank(r):
        return (_LABEL_PRIORITY.get(r.entity_type, 1), float(r.score), r.end - r.start)

    covered = set()
    kept = []
    for r in sorted(results, key=rank, reverse=True):
        span = range(r.start, r.end)
        if all(i in covered for i in span):
            continue  # every character already masked by a higher-ranked span
        kept.append(r)
        covered.update(span)
    return sorted(kept, key=lambda r: r.start)


def get_analyzer():
    # Lightweight spaCy tokenizer for Dutch (no BERTje download needed) — the
    # actual PII detection is done by the fine-tuned MedRoBERTa recognizer below.
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "nl", "model_name": "nl_core_news_sm"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry(supported_languages=["nl"])

    # Fine-tuned MedRoBERTa.nl PII model (primary detector)
    registry.add_recognizer(MedRobertaPIIRecognizer())

    # Custom Dutch/Belgian regex recognizers (INSZ, RIZIV, IBAN, phone, ...)
    for recognizer in get_dutch_regex_recognizers():
        registry.add_recognizer(recognizer)

    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=["nl"],
    )


def get_anonymizer():
    return AnonymizerEngine()


class PIIDetector:
    def __init__(self):
        self.analyzer = get_analyzer()
        self.anonymizer = get_anonymizer()

    def redact_text(self, text: str) -> str:
        if not text or not text.strip():
            return text

        results = self.analyzer.analyze(text=text, language="nl")

        # Keep clinical content visible; redact only identifying entities.
        results = [r for r in results if r.entity_type not in KEEP_VISIBLE]
        # Collapse overlapping model+regex hits to one label each.
        results = resolve_overlaps(results)
        if not results:
            return text

        # Replace each entity with a labelled placeholder, e.g. <PATIENT_NAME>.
        entity_types = {r.entity_type for r in results}
        operators = {
            et: OperatorConfig("replace", {"new_value": f"<{et}>"}) for et in entity_types
        }
        operators["DEFAULT"] = OperatorConfig("replace", {"new_value": "<REDACTED>"})

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text


# Singleton instance
detector = None


def get_detector():
    global detector
    if detector is None:
        detector = PIIDetector()
    return detector
