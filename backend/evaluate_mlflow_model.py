import json
import argparse
import mlflow
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Evaluate an MLflow model using a JSONL dataset with ground truth.")
    parser.add_argument("--model-uri", type=str, required=True, 
                        help="MLflow Model URI (e.g., 'runs:/<run_id>/model')")
    parser.add_argument("--dataset", type=str, required=True, 
                        help="Path to the JSONL evaluation dataset")
    args = parser.parse_args()

    print(f"Loading MLflow model from: {args.model_uri}")
    try:
        loaded_model = mlflow.pyfunc.load_model(args.model_uri)
        print("Model loaded successfully.\n")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print(f"Reading dataset from: {args.dataset}")
    texts = []
    ground_truths = []
    
    try:
        with open(args.dataset, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    # Use 'source_text' as the text to predict on
                    if "source_text" in data:
                        texts.append(data["source_text"])
                        # Store ground truth mask if available
                        ground_truths.append(data.get("privacy_mask", []))
                    else:
                        print(f"Warning: 'source_text' not found in a line.")
    except Exception as e:
        print(f"Error reading dataset: {e}")
        return
        
    print(f"Loaded {len(texts)} documents. Running predictions...")
    
    # MLflow typically expects a DataFrame
    test_df = pd.DataFrame({"text": texts})
    
    try:
        # Run inference
        predictions = loaded_model.predict(test_df)
    except Exception as e:
        print(f"Prediction failed with DataFrame format. Error: {e}")
        print("Trying with a list of strings instead...")
        try:
            predictions = loaded_model.predict(texts)
        except Exception as e2:
             print(f"Prediction failed with list of strings. Error: {e2}")
             return

    print("\nEvaluating Predictions (Character-level)...")
    
    TP = 0
    FP = 0
    FN = 0

    # Ensure predictions is iterable (some models return a pandas Series or list)
    if isinstance(predictions, pd.Series) or isinstance(predictions, pd.DataFrame):
         # If dataframe, take the first column or assume the output structure
         if isinstance(predictions, pd.DataFrame):
              predictions = predictions.iloc[:, 0].tolist()
         else:
              predictions = predictions.tolist()

    for idx, (text, gt_spans, pred_res) in enumerate(zip(texts, ground_truths, predictions)):
        
        # 1. Ground truth char array
        gt_chars = [False] * len(text)
        for span in gt_spans:
            start = span["start"]
            end = span["end"]
            for i in range(start, end):
                if i < len(text):
                    gt_chars[i] = True
                    
        # 2. Predicted char array
        pred_chars = [False] * len(text)
        
        # Handle different prediction formats that the MLflow model might output
        if isinstance(pred_res, str):
             # Try parsing if it's a JSON string
             try:
                 pred_res = json.loads(pred_res)
             except:
                 pred_res = []
                 
        if isinstance(pred_res, list):
            for res in pred_res:
                # Some models might return score, assume 0.4 threshold if score exists, otherwise take all
                if isinstance(res, dict) and "start" in res and "end" in res:
                    score = res.get("score", 1.0)
                    if score > 0.4:
                        for i in range(res["start"], res["end"]):
                            if i < len(text):
                                pred_chars[i] = True

        # 3. Compare
        for i in range(len(text)):
            if gt_chars[i] and pred_chars[i]:
                TP += 1
            elif not gt_chars[i] and pred_chars[i]:
                FP += 1
            elif gt_chars[i] and not pred_chars[i]:
                FN += 1

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n" + "="*40)
    print("--- MLFLOW MODEL EVALUATION METRICS ---")
    print("="*40)
    print(f"Total Documents Evaluated: {len(texts)}")
    print(f"True Positives (Chars): {TP:,}")
    print(f"False Positives (Chars): {FP:,}")
    print(f"False Negatives (Chars): {FN:,}")
    print("-" * 40)
    print(f"Precision: {precision:.4f} ({(precision*100):.1f}%)")
    print(f"Recall:    {recall:.4f} ({(recall*100):.1f}%)")
    print(f"F1 Score:  {f1:.4f} ({(f1*100):.1f}%)")
    print("="*40)

if __name__ == "__main__":
    main()
