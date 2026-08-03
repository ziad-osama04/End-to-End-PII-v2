import json
import argparse
import mlflow
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Test an MLflow model locally with a JSONL file.")
    parser.add_argument("--model-uri", type=str, required=True, 
                        help="MLflow Model URI (e.g., 'runs:/<run_id>/model' or 'models:/<model_name>/<version>')")
    parser.add_argument("--test-file", type=str, required=True, 
                        help="Path to the JSONL test file")
    parser.add_argument("--text-column", type=str, default="text", 
                        help="The key in the JSONL file containing the text to predict (default: 'text')")
    
    args = parser.parse_args()

    print(f"Loading MLflow model from: {args.model_uri}")
    try:
        # Load the model directly into memory
        loaded_model = mlflow.pyfunc.load_model(args.model_uri)
        print("Model loaded successfully.\n")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print(f"Reading test data from: {args.test_file}")
    texts = []
    try:
        with open(args.test_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if args.text_column in data:
                        texts.append(data[args.text_column])
                    else:
                        print(f"Warning: Column '{args.text_column}' not found in line: {line.strip()}")
    except FileNotFoundError:
        print(f"Error: Test file not found at {args.test_file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSONL: {e}")
        return
        
    print(f"Loaded {len(texts)} samples. Running predictions...\n")
    
    # We pass data as a pandas DataFrame as expected by most MLflow pyfunc flavors
    test_df = pd.DataFrame({args.text_column: texts})
    
    try:
        # Run inference
        predictions = loaded_model.predict(test_df)
        
        # Print results
        for idx, (text, pred) in enumerate(zip(texts, predictions)):
            print(f"--- Sample {idx + 1} ---")
            print(f"Text: {text}")
            print(f"Prediction: {pred}\n")
            
    except Exception as e:
        print(f"Error during prediction: {e}")
        print("Tip: If the model expects a different input format (e.g., raw list of strings instead of DataFrame), you might need to modify how test_df is passed to loaded_model.predict()")

if __name__ == "__main__":
    main()
