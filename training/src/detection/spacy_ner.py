from presidio_analyzer.nlp_engine import SpacyNlpEngine

def get_spacy_nlp_engine():
    """Returns a SpacyNlpEngine configured for Dutch."""
    return SpacyNlpEngine(models=[{"lang_code": "nl", "model_name": "nl_core_news_lg"}])
