from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from src.detection.dutch_regex import get_dutch_regex_recognizers
from src.detection.transformers_recognizer import MedRobertaPIIRecognizer

# Entity types the model detects but that we KEEP visible by default (clinical
# content, not identity). Add/remove here to change what gets redacted.
KEEP_VISIBLE = {"CLINICAL_NOTE", "MEDICATION"}


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
