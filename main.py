import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import re
from datetime import datetime

# --- CONFIGURATION ---
# If Tesseract is not in your PATH, uncomment and set the path below:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class PDFParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Parsing Tool (Power Query Ready)")
        self.root.geometry("700x550")
        
        self.file_list = []
        
        # --- UI LAYOUT ---
        
        # 1. Top Frame: File Selection & Options
        frame_top = tk.Frame(root, padx=10, pady=10)
        frame_top.pack(fill=tk.X)
        
        lbl_instruction = tk.Label(frame_top, text="Select PDFs to parse:")
        lbl_instruction.pack(side=tk.LEFT)
        
        btn_browse = tk.Button(frame_top, text="Browse Files", command=self.browse_files)
        btn_browse.pack(side=tk.RIGHT)
        
        # OCR Option (Checkbox)
        self.use_ocr_var = tk.BooleanVar(value=False)
        chk_ocr = tk.Checkbutton(frame_top, text="Force OCR (Slower)", variable=self.use_ocr_var)
        chk_ocr.pack(side=tk.RIGHT, padx=10)

        # 2. Middle Frame: Listbox for files
        frame_list = tk.Frame(root, padx=10, pady=5)
        frame_list.pack(fill=tk.BOTH, expand=True)
        
        self.listbox = tk.Listbox(frame_list, selectmode=tk.MULTIPLE)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(frame_list, orient="vertical")
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # 3. Bottom Frame: Actions & Status
        frame_bottom = tk.Frame(root, padx=10, pady=20)
        frame_bottom.pack(fill=tk.X)
        
        self.progress = ttk.Progressbar(frame_bottom, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # Process Button
        btn_process = tk.Button(frame_bottom, text="Process & Save CSV", command=self.process_files, bg="#007acc", fg="white", font=("Segoe UI", 10, "bold"))
        btn_process.pack(fill=tk.X)
        
        self.status_lbl = tk.Label(frame_bottom, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_lbl.pack(fill=tk.X, pady=(10, 0))

    def browse_files(self):
        """Handle File Dialog"""
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        if files:
            self.file_list = list(files)
            self.listbox.delete(0, tk.END)
            for f in files:
                self.listbox.insert(tk.END, os.path.basename(f))
            self.status_lbl.config(text=f"{len(files)} files selected.")

    def extract_text(self, file_path):
        """
        1. Tries to extract text using PyMuPDF (fast).
        2. Falls back to OCR (pdf2image + pytesseract) if text is empty or OCR is forced.
        """
        text_content = ""
        method_used = "Digital Extract"
        
        try:
            # 1. Try Digital Extraction (PyMuPDF)
            if not self.use_ocr_var.get():
                doc = fitz.open(file_path)
                for page in doc:
                    text_content += page.get_text() + "\n"
                doc.close()
            
            # 2. Check if OCR is needed (Empty text found OR Force OCR is checked)
            if self.use_ocr_var.get() or len(text_content.strip()) < 5:
                method_used = "OCR (Image Scan)"
                self.status_lbl.config(text=f"Running OCR on: {os.path.basename(file_path)}...")
                self.root.update()
                
                # Convert PDF pages to images
                images = convert_from_path(file_path)
                text_content = ""
                for img in images:
                    text_content += pytesseract.image_to_string(img) + "\n"
                    
        except Exception as e:
            print(f"Extraction Error: {e}")
            return "", "Error"

        return text_content, method_used

    def parse_data(self, text, filename, method):
        """
        CUSTOM PARSING LOGIC - Returns a dictionary (Single CSV Row)
        """
        data = {
            "Filename": filename,
            "Method": method,
            "Date_Processed": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # --- REGEX PATTERNS (Customize these!) ---
        
        # 1. Invoice Number (Example: "Invoice # 12345")
        # Looks for "Invoice" followed by optional space/hash, then the number
        inv_match = re.search(r'Invoice\s*#?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
        data['Invoice_No'] = inv_match.group(1) if inv_match else ""

        # 2. Date (Example: "12/05/2023" or "2023-05-12")
        date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})', text)
        data['Date'] = date_match.group(1) if date_match else ""

        # 3. Total Amount (Example: "$ 1,250.00")
        amount_match = re.search(r'\$\s?([\d,]+\.\d{2})', text)
        data['Total_Amount'] = amount_match.group(1) if amount_match else ""

        return data

    def process_files(self):
        if not self.file_list:
            messagebox.showwarning("Warning", "No files selected.")
            return

        # Ask where to save the CSV
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not save_path:
            return

        self.progress['maximum'] = len(self.file_list)
        results = []

        # PROCESSING LOOP
        for idx, file_path in enumerate(self.file_list):
            filename = os.path.basename(file_path)
            self.status_lbl.config(text=f"Processing {idx + 1}/{len(self.file_list)}: {filename}")
            self.root.update() # Keep UI responsive

            try:
                # 1. Extract
                raw_text, method = self.extract_text(file_path)
                
                # 2. Parse
                row_data = self.parse_data(raw_text, filename, method)
                results.append(row_data)
                
            except Exception as e:
                # Log error in CSV so you don't lose the whole batch
                results.append({"Filename": filename, "Error": str(e)})

            self.progress['value'] = idx + 1

        # Save to CSV
        try:
            df = pd.DataFrame(results)
            df.to_csv(save_path, index=False)
            messagebox.showinfo("Done", f"Processing complete.\nSaved to: {save_path}")
            self.status_lbl.config(text="Processing Complete.")
        except Exception as e:
            messagebox.showerror("Error Saving", str(e))
        finally:
            self.progress['value'] = 0

def main():
    root = tk.Tk()
    PDFParserApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()