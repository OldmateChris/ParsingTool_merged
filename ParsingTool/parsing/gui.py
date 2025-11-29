import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import pandas as pd  # currently unused, but OK to keep
import shutil

from .export_orders.pipeline import parse_export_pdf
from .domestic_zapi import pipeline as domestic_pipeline
from .qc import validate, write_report
from .merge_with_overrides import apply_overrides

# ---------------------------------------------------------------------------
# THEME SETTINGS (edit these to change look & feel)
# ---------------------------------------------------------------------------

# Window + panels
BG_MAIN   = "#acacac"   # main window background
BG_STATUS = "#302f2f"   # status bar background

# Text entry fields
ENTRY_BG = "#686868"    # entry field background
ENTRY_FG = "#65F008"    # entry field text colour

# Log area
LOG_BG = "#0C0C0C"      # log box background
LOG_FG = "#65F008"      # log box text colour

# Buttons
BUTTON_BG        = "#444444"  # normal button background
BUTTON_FG        = "#ffffff"  # normal button text
BUTTON_ACTIVE_BG = "#666666"  # background while pressed/hovered
BUTTON_ACTIVE_FG = "#ffffff"  # text while pressed/hovered

# Scrollbar on log
SCROLLBAR_BG        = "#444444"  # colour of the scrollbar handle
SCROLLBAR_TROUGH    = "#222222"  # colour of the track behind it
SCROLLBAR_ACTIVE_BG = "#666666"  # colour when you hover/drag

# General text colours
FG_TEXT  = "#202124"   # label / checkbox text colour
FG_MUTED = "#5f6368"   # slightly lighter text (optional)
FG_OK    = "#65F008"   # green for "OK" status
FG_ERROR = "#ff0000"   # red for "missing" / error status

# Fonts
FONT_LABEL  = ("Ubuntu", 10)
FONT_ENTRY  = ("Share Tech Mono", 10)
FONT_BUTTON = ("Ubuntu", 11)
FONT_CHECK  = ("Ubuntu", 10)
FONT_LOG    = ("JetBrainsMono NF", 9)
FONT_STATUS = ("Inconsolata ExtraExpanded", 10, "bold")


def run_gui() -> None:
    """Launch the Tkinter GUI for the ParsingTool."""

    # Root window
    root = tk.Tk()
    root.title("ParsingTool")
    root.configure(bg=BG_MAIN)

    # Layout config
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)   # main stretch
    root.columnconfigure(2, weight=0)

    root.rowconfigure(6, weight=1)      # log box stretches vertically
    root.rowconfigure(7, weight=0)      # status bar stays fixed

    # -------------------------------------------------------------------
    # INPUT FIELDS (entries)
    # -------------------------------------------------------------------

    file_entry = tk.Entry(
        root,
        width=60,
        font=FONT_ENTRY,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
    )

    folder_entry = tk.Entry(
        root,
        width=60,
        font=FONT_ENTRY,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
    )

    output_entry = tk.Entry(
        root,
        width=60,
        font=FONT_ENTRY,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
    )

    # --- Browse handlers ---

    def browse_file() -> None:
        p = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if p:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, p)

    def browse_folder() -> None:
        p = filedialog.askdirectory()
        if p:
            folder_entry.delete(0, tk.END)
            folder_entry.insert(0, p)

    def browse_output() -> None:
        p = filedialog.askdirectory()
        if p:
            output_entry.delete(0, tk.END)
            output_entry.insert(0, p)

    # -------------------------------------------------------------------
    # OPTIONS (checkbox / radio state)
    # -------------------------------------------------------------------

    debug_var = tk.BooleanVar(value=False)
    ocr_var = tk.BooleanVar(value=False)
    qc_var = tk.BooleanVar(value=True)
    mode_var = tk.StringVar(value="export")  # "export" or "domestic"

    # -------------------------------------------------------------------
    # LOG BOX + SCROLLBAR
    # -------------------------------------------------------------------

    log_box = scrolledtext.ScrolledText(root, height=18)
    log_box.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

    log_box.configure(
        bg=LOG_BG,
        fg=LOG_FG,
        font=FONT_LOG,
        insertbackground=LOG_FG,
    )

    try:
        vbar = log_box.vbar
        vbar.configure(
            bg=SCROLLBAR_BG,
            troughcolor=SCROLLBAR_TROUGH,
            activebackground=SCROLLBAR_ACTIVE_BG,
            highlightthickness=0,
            bd=0,
        )
    except AttributeError:
        pass

    # -------------------------------------------------------------------
    # LOGGING HELPER
    # -------------------------------------------------------------------

    def log(msg: str) -> None:
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)

    # -------------------------------------------------------------------
    # MAIN PROCESSING LOGIC
    # -------------------------------------------------------------------

    def process() -> None:
        outdir = Path(output_entry.get().strip() or ".")
        file_path = file_entry.get().strip()
        folder_path = folder_entry.get().strip()

        pdfs: list[Path] = []
        if file_path:
            pdfs = [Path(file_path)]
        elif folder_path:
            pdfs = sorted(Path(folder_path).glob("*.pdf"))
        else:
            messagebox.showerror("Error", "Choose a file or a folder")
            return

        outdir.mkdir(parents=True, exist_ok=True)
        qc_results: list = []

        mode = mode_var.get() or "export"

        for p in pdfs:
            try:
                if mode == "domestic":
                    # Domestic pipeline: writes 2 CSVs (batches + SSCC)
                    base = p.stem
                    batches_out = outdir / f"{base}_batches.csv"
                    sscc_out = outdir / f"{base}_sscc.csv"

                    domestic_pipeline.run(
                        input_pdf=str(p),
                        out_batches=str(batches_out),
                        out_sscc=str(sscc_out),
                    )
                    
                    log(f"[saved] {batches_out}")
                    log(f"[saved] {sscc_out}")

                else:
                    # Export pipeline: one-row CSV + QC
                    df = parse_export_pdf(
                        p,
                        debug=debug_var.get(),
                        use_ocr=ocr_var.get(),
                    )
                    base = (df.iloc[0].get("Delivery Number") or "").strip() or p.stem
                    out = outdir / f"parsed_{base}.csv"
                    df.to_csv(out, index=False, encoding="utf-8-sig")
                    log(f"[saved] {out}")
                    qc_results.append(validate(df, p.name))

            except Exception as e:  # GUI error path
                log(f"[error] {p}: {e}")

        # QC/report only makes sense for export mode
        if mode == "export" and qc_var.get():
            report_path = outdir / "qc_report.md"
            write_report(qc_results, report_path)
            log(f"[qc] wrote {report_path}")
        elif mode == "domestic" and qc_var.get():
            log("[qc] Note: QC report is only implemented for export mode; skipping.")

    # -------------------------------------------------------------------
    # LAYOUT: LABELS, ENTRIES, BROWSE BUTTONS
    # -------------------------------------------------------------------

    tk.Label(root, text="Single PDF:", bg=BG_MAIN, fg=FG_TEXT, font=FONT_LABEL).grid(
        row=0, column=0, sticky="e", padx=10, pady=5
    )
    file_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
    tk.Button(
        root,
        text="Browse",
        command=browse_file,
        font=FONT_BUTTON,
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        activebackground=BUTTON_ACTIVE_BG,
        activeforeground=BUTTON_ACTIVE_FG,
    ).grid(row=0, column=2, sticky="e", padx=10, pady=5)

    tk.Label(root, text="Folder of PDFs:", bg=BG_MAIN, fg=FG_TEXT, font=FONT_LABEL).grid(
        row=1, column=0, sticky="e", padx=10, pady=5
    )
    folder_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
    tk.Button(
        root,
        text="Browse",
        command=browse_folder,
        font=FONT_BUTTON,
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        activebackground=BUTTON_ACTIVE_BG,
        activeforeground=BUTTON_ACTIVE_FG,
    ).grid(row=1, column=2, sticky="e", padx=10, pady=5)

    tk.Label(root, text="Output Folder:", bg=BG_MAIN, fg=FG_TEXT, font=FONT_LABEL).grid(
        row=2, column=0, sticky="e", padx=10, pady=5
    )
    output_entry.grid(row=2, column=1, sticky="we", padx=5, pady=5)
    tk.Button(
        root,
        text="Browse",
        command=browse_output,
        font=FONT_BUTTON,
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        activebackground=BUTTON_ACTIVE_BG,
        activeforeground=BUTTON_ACTIVE_FG,
    ).grid(row=2, column=2, sticky="e", padx=10, pady=5)

    # -------------------------------------------------------------------
    # CHECKBOX OPTIONS
    # -------------------------------------------------------------------

    tk.Checkbutton(
        root,
        text="Debug logs",
        variable=debug_var,
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).grid(row=3, column=0, sticky="w", padx=(10, 0), pady=5)

    tk.Checkbutton(
        root,
        text="Write QC report",
        variable=qc_var,
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).grid(row=3, column=1, sticky="", padx=(10, 0), pady=5)

    tk.Checkbutton(
        root,
        text="Use OCR fallback",
        variable=ocr_var,
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).grid(row=3, column=2, sticky="w", padx=(10, 10), pady=5)

    # -------------------------------------------------------------------
    # MODE SELECTION (Export vs Domestic)
    # -------------------------------------------------------------------

    tk.Label(
        root,
        text="Mode:",
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=FONT_LABEL,
    ).grid(row=4, column=0, sticky="e", padx=10, pady=5)

    tk.Radiobutton(
        root,
        text="Export (single-order CSV)",
        variable=mode_var,
        value="export",
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=FONT_CHECK,
        anchor="w",
    ).grid(row=4, column=1, sticky="w", padx=(10, 0), pady=5)

    tk.Radiobutton(
        root,
        text="Domestic (batches + SSCC)",
        variable=mode_var,
        value="domestic",
        bg=BG_MAIN,
        fg=FG_TEXT,
        font=FONT_CHECK,
        anchor="e",
    ).grid(row=4, column=2, sticky="e", padx=(10, 10), pady=5)

    # -------------------------------------------------------------------
    # PROCESS BUTTON
    # -------------------------------------------------------------------

    tk.Button(
        root,
        text="Process",
        command=process,
        font=FONT_BUTTON,
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        activebackground=BUTTON_ACTIVE_BG,
        activeforeground=BUTTON_ACTIVE_FG,
    ).grid(row=5, column=1, pady=10)

    # -------------------------------------------------------------------
    # TESSERACT / POPPLER STATUS BAR
    # -------------------------------------------------------------------

    def is_installed(cmd: str) -> bool:
        return shutil.which(cmd) is not None

    status_bar = tk.Frame(root, bg=BG_STATUS)
    status_bar.grid(row=7, column=0, columnspan=3, sticky="we")
    status_bar.grid_columnconfigure(0, weight=1)
    status_bar.grid_columnconfigure(1, weight=1)

    tesseract_ok = is_installed("tesseract")
    tess_colour = FG_OK if tesseract_ok else FG_ERROR

    tk.Label(
        status_bar,
        text="TESSERACT",
        fg=tess_colour,
        bg=BG_STATUS,
        font=FONT_STATUS,
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=10, pady=3)

    poppler_ok = is_installed("pdftoppm") or is_installed("pdfinfo")
    poppler_colour = FG_OK if poppler_ok else FG_ERROR

    tk.Label(
        status_bar,
        text="POPPLER",
        fg=poppler_colour,
        bg=BG_STATUS,
        font=FONT_STATUS,
        anchor="e",
    ).grid(row=0, column=1, sticky="e", padx=10, pady=3)

    root.mainloop()


if __name__ == "__main__":
    run_gui()
