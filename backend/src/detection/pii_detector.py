from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from src.detection.dutch_regex import get_dutch_regex_recognizers

def get_analyzer():
    # Configure the Transformers NLP engine for Dutch using MedRoBERTa
    configuration = {
        "nlp_engine_name": "transformers",
        "models": [
            {
                "lang_code": "nl",
                "model_name": {
                    "spacy": "nl_core_news_sm",
                    "transformers": "Babelscape/wikineural-multilingual-ner"
                }
            }
        ]
    }
    
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    
    # Initialize the registry and add our custom Dutch regex recognizers
    registry = RecognizerRegistry(supported_languages=["nl"])
    registry.load_predefined_recognizers(nlp_engine=nlp_engine, languages=["nl"])
    
    for recognizer in get_dutch_regex_recognizers():
        registry.add_recognizer(recognizer)
        
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine, 
        registry=registry, 
        supported_languages=["nl"]
    )
    return analyzer

def get_anonymizer():
    return AnonymizerEngine()

class PIIDetector:
    def __init__(self):
        self.analyzer = get_analyzer()
        self.anonymizer = get_anonymizer()

    def redact_text(self, text: str) -> str:
        if not text or not text.strip():
            return text
            
        # Detect PII
        results = self.analyzer.analyze(text=text, language="nl")
        
        # Redact detected PII
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})}
        )
        return anonymized.text

# Singleton instance
detector = None
def get_detector():
    global detector
    if detector is None:
        detector = PIIDetector()
    return detector
