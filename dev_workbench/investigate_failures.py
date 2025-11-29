import pandas as pd
from ParsingTool.parsing.export_orders.pipeline import parse_export_pdf
from ParsingTool.parsing.shared.pdf_utils import extract_text
import os

OUTPUT_CSV = 'output/combined_results.csv'

def main():
    # 1. Load results
    if not os.path.exists(OUTPUT_CSV):
        print(f"Error: {OUTPUT_CSV} not found.")
        return

    df = pd.read_csv(OUTPUT_CSV)
    
    # 2. Filter for empty Variety
    # Check for NaN or empty string
    failed_df = df[df['Variety'].isna() | (df['Variety'].astype(str).str.strip() == '')]
    
    failed_files = failed_df['Source_File'].unique().tolist()
    
    print(f"Found {len(failed_files)} failed PDFs (Empty Variety).")
    print("--- First 5 Failed Filenames ---")
    for f in failed_files[:5]:
        print(f)
    print("--------------------------------\n")

    if not failed_files:
        print("No failed files found.")
        return

    # 3. Pick the first failed filename
    first_failed = failed_files[0]
    input_path = os.path.join('input', first_failed)
    
    print(f"Investigating first failure: {input_path}")
    
    # 5. Print FULL raw text with repr
    print("\n--- FULL RAW TEXT (repr) ---")
    try:
        raw_text = extract_text(input_path)
        print(repr(raw_text))
        if not raw_text.strip():
            print("\n[!] Text appears empty. This likely indicates a scanned PDF without OCR layer.")
    except Exception as e:
        print(f"Error extracting text: {e}")
    print("--- END RAW TEXT ---")

    # 6. Try with OCR if empty
    if not raw_text.strip():
        print("\n--- Attempting OCR extraction ---")
        try:
            # Force OCR
            ocr_text = extract_text(input_path, use_ocr=True)
            print(f"OCR Text Length: {len(ocr_text)}")
            print("OCR Text Preview (first 500 chars):")
            print(repr(ocr_text[:500]))
        except Exception as e:
            print(f"OCR failed: {e}")

if __name__ == "__main__":
    main()
