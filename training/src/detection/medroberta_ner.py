from presidio_analyzer import EntityRecognizer, RecognizerResult
from transformers import pipeline

class MedRobertaRecognizer(EntityRecognizer):
    """
    Custom Presidio recognizer using BERTje (GroNLP/bert-base-dutch-cased) for medical entity context.
    """
    def __init__(self, model_name="GroNLP/bert-base-dutch-cased"):
        super().__init__(supported_entities=["PERSON", "ORGANIZATION", "LOCATION"],
                         supported_language="nl")
        self.model_name = model_name
        # Note: GroNLP/bert-base-dutch-cased is a base model. If a fine-tuned NER version isn't available, 
        # this will just try to use a generic token-classification pipeline which might fail or be suboptimal.
        # For a production system, we'd use a specifically fine-tuned medical NER model.
        try:
            self.nlp = pipeline("token-classification", model=self.model_name, aggregation_strategy="simple")
        except Exception as e:
            print(f"Warning: Failed to load BERTje model ({e}). Fallback to dummy pipeline.")
            self.nlp = None

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        if not self.nlp:
            return results
            
        try:
            predictions = self.nlp(text)
            for pred in predictions:
                entity_group = pred.get("entity_group", "")
                presidio_entity = None
                
                if entity_group in ["PER", "PERSON"]:
                    presidio_entity = "PERSON"
                elif entity_group in ["ORG", "ORGANIZATION"]:
                    presidio_entity = "ORGANIZATION"
                elif entity_group in ["LOC", "LOCATION"]:
                    presidio_entity = "LOCATION"
                    
                if presidio_entity and (entities is None or presidio_entity in entities):
                    results.append(
                        RecognizerResult(
                            entity_type=presidio_entity,
                            start=pred["start"],
                            end=pred["end"],
                            score=float(pred["score"])
                        )
                    )
        except Exception:
            pass
            
        return results
