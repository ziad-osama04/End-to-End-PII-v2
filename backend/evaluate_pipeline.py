import json
import os
import sys

# Add backend to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.detection.pii_detector import get_analyzer

def main():
    print("Loading Analyzer Engine... (this may take a few seconds)")
    analyzer = get_analyzer()

    dataset_path = os.path.join("..", "data", "hf_ner_dataset.jsonl")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    print("Evaluating...")
    TP = 0
    FP = 0
    FN = 0

    docs_processed = 0
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            text = data["text"]
            gt_spans = data["spans"]
            
            # Ground truth char array
            gt_chars = [False] * len(text)
            for span in gt_spans:
                for i in range(span["start"], span["end"]):
                    if i < len(text):
                        gt_chars[i] = True
                        
            # Predicted
            results = analyzer.analyze(text=text, language="nl")
            pred_chars = [False] * len(text)
            for res in results:
                # ignore extremely low confidence or generic
                if res.score > 0.4:
                    for i in range(res.start, res.end):
                        if i < len(text):
                            pred_chars[i] = True
                        
            # Compare
            for i in range(len(text)):
                if gt_chars[i] and pred_chars[i]:
                    TP += 1
                elif not gt_chars[i] and pred_chars[i]:
                    FP += 1
                elif gt_chars[i] and not pred_chars[i]:
                    FN += 1
            docs_processed += 1
            
            # Print progress every 50 docs
            if docs_processed % 50 == 0:
                print(f"Processed {docs_processed} documents...")

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n" + "="*30)
    print("--- EVALUATION METRICS (Character-Level) ---")
    print("="*30)
    print(f"Total Documents Evaluated: {docs_processed}")
    print(f"True Positives (Chars): {TP:,}")
    print(f"False Positives (Chars): {FP:,}")
    print(f"False Negatives (Chars): {FN:,}")
    print("-" * 30)
    print(f"Precision: {precision:.4f} ({(precision*100):.1f}%)")
    print(f"Recall:    {recall:.4f} ({(recall*100):.1f}%)")
    print(f"F1 Score:  {f1:.4f} ({(f1*100):.1f}%)")
    print("="*30)

if __name__ == "__main__":
    main()
