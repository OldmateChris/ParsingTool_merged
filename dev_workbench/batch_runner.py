import os
import glob
import pandas as pd
from ParsingTool.parsing.export_orders.pipeline import parse_export_pdf

INPUT_DIR = 'input'
OUTPUT_FILE = 'output/combined_results.csv'

def main():
    pdf_files = glob.glob(os.path.join(INPUT_DIR, '*.pdf'))
    print(f"Found {len(pdf_files)} PDFs.")
    
    all_dfs = []
    for pdf_file in pdf_files:
        try:
            # print(f"Processing {pdf_file}...")
            df = parse_export_pdf(pdf_file, use_ocr=True)
            # Add source filename for traceability
            df['Source_File'] = os.path.basename(pdf_file)
            all_dfs.append(df)
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")

    if not all_dfs:
        print("No data collected.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved combined results to {OUTPUT_FILE}")

    print("\n--- AUDIT RESULTS ---")
    for col in ['Variety', 'Grade', 'Packaging']:
        if col in combined_df.columns:
            print(f"\nValue Counts for '{col}':")
            print(combined_df[col].value_counts().to_string())
        else:
            print(f"\nColumn '{col}' not found in results.")

if __name__ == "__main__":
    main()
