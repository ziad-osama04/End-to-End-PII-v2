import argparse
import sys
from config import ensure_directories
from src.extraction.pdf_extractor import run_extraction
from src.detection.pii_detector import run_detection
from src.pseudonymization.pseudonymizer import run_pseudonymization
from src.schema.schema_extractor import run_schema_extraction
from src.synthesis.recombiner import run_recombination
from src.synthesis.report_generator import run_report_generation
from src.validation.pii_validator import run_validation

def main():
    parser = argparse.ArgumentParser(description="End-to-End PII Pipeline")
    parser.add_argument("--phase", type=str, choices=["all", "extraction", "detection", "pseudonymize", "schema", "synthesize", "validate"], default="all")
    args = parser.parse_args()

    ensure_directories()

    try:
        if args.phase in ["all", "extraction"]:
            print("--- Running Phase 2: PDF Extraction ---")
            run_extraction()
        
        if args.phase in ["all", "detection"]:
            print("--- Running Phase 3: PII Detection ---")
            run_detection()
            
        if args.phase in ["all", "pseudonymize"]:
            print("--- Running Phase 4: Pseudonymization ---")
            run_pseudonymization()
            
        if args.phase in ["all", "schema"]:
            print("--- Running Phase 5: Schema Extraction ---")
            run_schema_extraction()
            
        if args.phase in ["all", "synthesize"]:
            print("--- Running Phase 6: Shuffle & Recombine ---")
            run_recombination()
            print("--- Running Phase 7: Synthetic Report Generation ---")
            run_report_generation()
            
        if args.phase in ["all", "validate"]:
            print("--- Running Phase 8: PII Validation ---")
            run_validation()
            
        print("Pipeline execution completed.")
        
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
