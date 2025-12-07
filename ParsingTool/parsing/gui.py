import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import shutil
import threading
import csv  # NEW

# --- PIPELINE IMPORTS ---
from .export_orders.pipeline import parse_export_pdf, run_batch as run_export_batch
from .domestic_zapi import pipeline as domestic_pipeline
from .packing_list.pipeline import run as run_packing_pipeline, run_batch as run_packing_batch
from .qc import validate, write_report
from .shared.pdf_utils import NoTextError  # NEW


# ---------------------------------------------------------------------------
# THEME SETTINGS
# ---------------------------------------------------------------------------
BG_MAIN = "#acacac"
BG_PANEL = "#b8b8b8"  # Slightly lighter for groups
BG_STATUS = "#302f2f"
ENTRY_BG = "#686868"
ENTRY_FG = "#65F008"
LOG_BG = "#0C0C0C"
LOG_FG = "#65F008"
BUTTON_BG = "#444444"
BUTTON_FG = "#ffffff"
FG_TEXT = "#202124"
FG_OK = "#65F008"
FG_ERROR = "#ff0000"
FG_MUTED = "#5f6368"

FONT_LABEL = ("Ubuntu", 10)
FONT_ENTRY = ("Share Tech Mono", 10)
FONT_BUTTON = ("Ubuntu", 11)
FONT_CHECK = ("Ubuntu", 10)
FONT_LOG = ("JetBrainsMono NF", 9)
FONT_STATUS_SIDE = ("Inconsolata ExtraExpanded", 9, "bold")  # smaller side labels
FONT_STATUS_MAIN = ("Inconsolata ExtraExpanded", 11, "bold")  # bigger center label
FONT_TITLE = ("Ubuntu", 11, "bold")  # For group headers


def is_installed(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_gui() -> None:
    root = tk.Tk()
    root.title("ParsingTool v2.0")
    root.configure(bg=BG_MAIN)
    root.update_idletasks()  # let Tkinter calculate needed size
    root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())


    # Layout: Main content expands, status bar fixed
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Main container frame to hold the "steps"
    main_frame = tk.Frame(root, bg=BG_MAIN, padx=10, pady=10)
    main_frame.grid(row=0, column=0, sticky="nsew")
    main_frame.columnconfigure(0, weight=1)

    # -------------------------------------------------------------------
    # STEP 1: INPUTS (LabelFrame)
    # -------------------------------------------------------------------
    step1 = tk.LabelFrame(
        main_frame,
        text=" 1. Select Files ",
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_TITLE,
    )
    step1.grid(row=0, column=0, sticky="ew", pady=(0, 10), ipady=5)
    step1.columnconfigure(1, weight=1)

    # File
    tk.Label(
        step1, text="Single PDF:", bg=BG_PANEL, fg=FG_TEXT, font=FONT_LABEL
    ).grid(row=0, column=0, sticky="e", padx=5, pady=5)
    file_entry = tk.Entry(
        step1,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
        font=FONT_ENTRY,
    )
    file_entry.grid(row=0, column=1, sticky="ew", padx=5)

    # Folder
    tk.Label(
        step1, text="OR Folder:", bg=BG_PANEL, fg=FG_TEXT, font=FONT_LABEL
    ).grid(row=1, column=0, sticky="e", padx=5, pady=5)
    folder_entry = tk.Entry(
        step1,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
        font=FONT_ENTRY,
    )
    folder_entry.grid(row=1, column=1, sticky="ew", padx=5)

    # Output
    tk.Label(
        step1, text="Output To:", bg=BG_PANEL, fg=FG_TEXT, font=FONT_LABEL
    ).grid(row=2, column=0, sticky="e", padx=5, pady=5)
    output_entry = tk.Entry(
        step1,
        bg=ENTRY_BG,
        fg=ENTRY_FG,
        insertbackground=ENTRY_FG,
        font=FONT_ENTRY,
    )
    output_entry.grid(row=2, column=1, sticky="ew", padx=5)

    # Buttons
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

    tk.Button(step1, text="Browse", command=browse_file, bg=BUTTON_BG, fg=BUTTON_FG).grid(
        row=0, column=2, padx=5
    )
    tk.Button(step1, text="Browse", command=browse_folder, bg=BUTTON_BG, fg=BUTTON_FG).grid(
        row=1, column=2, padx=5
    )
    tk.Button(step1, text="Browse", command=browse_output, bg=BUTTON_BG, fg=BUTTON_FG).grid(
        row=2, column=2, padx=5
    )

    # -------------------------------------------------------------------
    # STEP 2: MODE (LabelFrame)
    # -------------------------------------------------------------------
    step2 = tk.LabelFrame(
        main_frame,
        text=" 2. Document Type ",
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_TITLE,
    )
    step2.grid(row=1, column=0, sticky="ew", pady=(0, 10), ipady=5)

    mode_var = tk.StringVar(value="export")

    tk.Radiobutton(
        step2,
        text="Export Orders",
        variable=mode_var,
        value="export",
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).pack(side="left", padx=20)

    tk.Radiobutton(
        step2,
        text="Domestic ZAPI",
        variable=mode_var,
        value="domestic",
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).pack(side="left", padx=20)

    tk.Radiobutton(
        step2,
        text="Packing List (PI)",
        variable=mode_var,
        value="packinglist",
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).pack(side="left", padx=20)

    # -------------------------------------------------------------------
    # STEP 3: OPTIONS (LabelFrame - "Advanced")
    # -------------------------------------------------------------------
    step3 = tk.LabelFrame(
        main_frame,
        text=" 3. Advanced Options ",
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_TITLE,
    )
    step3.grid(row=2, column=0, sticky="ew", pady=(0, 10), ipady=5)

    debug_var = tk.BooleanVar(value=False)
    ocr_var = tk.BooleanVar(value=False)
    qc_var = tk.BooleanVar(value=True)
    combine_var = tk.BooleanVar(value=False)

    ocr_check = tk.Checkbutton(
        step3,
        text="Enable OCR Fallback (Slow)",
        variable=ocr_var,
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    )
    ocr_check.pack(side="left", padx=10)

    tk.Checkbutton(
        step3,
        text="Generate QC Report (Export Only)",
        variable=qc_var,
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).pack(side="left", padx=10)

    tk.Checkbutton(
        step3,
        text="Show Debug Logs",
        variable=debug_var,
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).pack(side="left", padx=10)

    tk.Checkbutton(
        step3,
        text="Combine folder results into one CSV",
        variable=combine_var,
        bg=BG_PANEL,
        fg=FG_TEXT,
        font=FONT_CHECK,
    ).pack(side="left", padx=10)

    # -------------------------------------------------------------------
    # LOG & ACTION
    # -------------------------------------------------------------------
    process_btn = tk.Button(
        main_frame,
        text="PROCESS FILES",
        font=("Ubuntu", 12, "bold"),
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        height=2,
        width=20,
    )
    process_btn.grid(row=3, column=0, pady=10)

    log_label = tk.Label(
        main_frame, text="Processing Log:", bg=BG_MAIN, fg=FG_TEXT, font=FONT_LABEL
    )
    log_label.grid(row=4, column=0, sticky="w")

    log_box = scrolledtext.ScrolledText(
        main_frame, height=10, bg=LOG_BG, fg=LOG_FG, font=FONT_LOG
    )
    log_box.grid(row=5, column=0, sticky="nsew")
    main_frame.rowconfigure(5, weight=1)  # Log expands

    def log(msg: str) -> None:
        def _insert() -> None:
            log_box.insert(tk.END, msg + "\n")
            log_box.see(tk.END)

        root.after(0, _insert)

    # -------------------------------------------------------------------
    # LOGIC
    # -------------------------------------------------------------------
    def run_processing_thread(
        pdfs, outdir, mode, debug, use_ocr, run_qc, combine, folder_path
    ) -> None:
        """Process a list of PDFs and write their CSV outputs.

        Args:
            pdfs: Iterable of Path objects for input PDFs.
            outdir: Path to output directory.
            mode: One of "export", "domestic", "packinglist".
            debug: Whether to enable debug logging.
            use_ocr: Whether to enable OCR fallback.
            run_qc: Whether to run QC (export mode only).
            combine: whether to combine outputs.
            folder_path: original folder path string.
        """
        try:
            log(f"--- Starting {mode.upper()} mode on {len(pdfs)} file(s) ---")
            qc_results = []

            # If user asked to combine and gave us a folder, use the batch pipelines
            folder = Path(folder_path) if folder_path else None
            if combine and folder is not None and folder.is_dir():
                log("Combine mode enabled: creating combined CSV(s) from folder.")

                if mode == "export":
                    run_export_batch(folder, outdir, use_ocr=use_ocr, debug=debug)
                    combined = outdir / "export_combined.csv"
                    log(f"[COMBINED] Wrote {combined.name}")

                elif mode == "domestic":
                    domestic_pipeline.run_batch(
                        folder, outdir, use_ocr=use_ocr, debug=debug
                    )
                    log(
                        "[COMBINED] Wrote domestic_batches_combined.csv "
                        "and domestic_sscc_combined.csv"
                    )

                elif mode == "packinglist":
                    run_packing_batch(
                        folder,
                        outdir,
                        use_ocr=use_ocr,
                        debug=debug,
                    )
                    combined = outdir / "pi_combined.csv"
                    log(f"[COMBINED] Wrote {combined.name}")

                else:
                    log(f"[WARN] Combine is not supported for mode: {mode}")

                log("--- Completed ---")
                return

            # Normal per-file processing
            for p in pdfs:
                try:
                    if mode == "export":
                        name_upper = p.name.upper()

                        # Auto-route PI / ZAPI files to the PI pipeline
                        if name_upper.endswith("_PI.PDF") or name_upper.endswith("_ZAPI.PDF"):
                            out_csv = outdir / f"{p.stem}_packing.csv"
                            run_packing_pipeline(
                            input_pdf=str(p),
                            out=str(out_csv),
                            use_ocr=use_ocr,
                            debug=debug,
                        )
                            log(f"[OK][PI] {p.name} -> {out_csv.name}")

                        else:
                            # Normal export pipeline
                            df = parse_export_pdf(
                                str(p), use_ocr=use_ocr, debug=debug
                            )
                            out_csv = outdir / f"{p.stem}.csv"
                            df.to_csv(out_csv, index=False, encoding="utf-8-sig")
                            log(
                                f"[OK] {p.name} -> {out_csv.name} "
                                f"({len(df)} rows)"
                            )

                            if run_qc:
                                qc_results.append(validate(df, p.name))

                    elif mode == "domestic":
                        batches_csv = outdir / f"{p.stem}_batches.csv"
                        sscc_csv = outdir / f"{p.stem}_sscc.csv"

                        domestic_pipeline.run(
                            input_pdf=str(p),
                            out_batches=str(batches_csv),
                            out_sscc=str(sscc_csv),
                            use_ocr=use_ocr,
                            debug=debug,
                        )
                        log(
                            f"[OK] {p.name} -> "
                            f"{batches_csv.name}, {sscc_csv.name}"
                        )

                    elif mode == "packinglist":
                        out_csv = outdir / f"{p.stem}_packing.csv"
                        run_packing_pipeline(
                            input_pdf=str(p),
                            out=str(out_csv),
                            use_ocr=use_ocr,
                            debug=debug,
                        )
                        log(f"[OK] {p.name} -> {out_csv.name}")

                    else:
                        log(f"[WARN] Unknown mode: {mode}")

                except NoTextError as e:
                    log(f"[WARN] {p.name}: no extractable text ({e})")
                except Exception as e:
                    log(f"[ERROR] {p.name}: {e}")

            # QC report for export
            if mode == "export" and run_qc and qc_results:
                report_path = outdir / "qc_report.md"
                write_report(qc_results, report_path)
                log(f"[QC] Wrote report: {report_path.name}")

            log("--- Completed ---")

        except Exception as e:
            log(f"[FATAL] {e}")
        finally:
            root.after(
                0, lambda: process_btn.config(state=tk.NORMAL, text="PROCESS FILES")
            )

    def start_process() -> None:
        outdir = Path(output_entry.get().strip() or ".")
        file_path = file_entry.get().strip()
        folder_path = folder_entry.get().strip()

        pdfs = []
        if file_path:
            pdfs = [Path(file_path)]
        elif folder_path:
            pdfs = sorted(Path(folder_path).glob("*.pdf"))

        if not pdfs:
            messagebox.showerror("Error", "Please select a file or folder first.")
            return

        outdir.mkdir(parents=True, exist_ok=True)
        process_btn.config(state=tk.DISABLED, text="Running...")

        mode = mode_var.get()
        t = threading.Thread(
            target=run_processing_thread,
            args=(
                pdfs,
                outdir,
                mode,
                debug_var.get(),
                ocr_var.get(),
                qc_var.get(),
                combine_var.get(),
                folder_path,
            ),
            daemon=True,
        )
        t.start()

    process_btn.config(command=start_process)

    # -------------------------------------------------------------------
    # STATUS BAR
    # -------------------------------------------------------------------
    status = tk.Frame(root, bg=BG_STATUS)
    status.grid(row=1, column=0, sticky="ew")

    status.columnconfigure(0, weight=1)
    status.columnconfigure(1, weight=0)
    status.columnconfigure(2, weight=1)

    tess_lbl = tk.Label(
        status,
        text="TESSERACT OCR",
        bg=BG_STATUS,
        fg=FG_MUTED,
        font=FONT_STATUS_SIDE,
    )
    tess_lbl.grid(row=0, column=0, sticky="w", padx=10)

    ocr_status_lbl = tk.Label(
        status,
        text="CHECKING OCR...",
        bg=BG_STATUS,
        fg=FG_MUTED,
        font=FONT_STATUS_MAIN,
    )
    ocr_status_lbl.grid(row=0, column=1)

    popp_lbl = tk.Label(
        status,
        text="POPPLER UTILS",
        bg=BG_STATUS,
        fg=FG_MUTED,
        font=FONT_STATUS_SIDE,
    )
    popp_lbl.grid(row=0, column=2, sticky="e", padx=10)

    def update_ocr_status() -> None:
        tess_ok = is_installed("tesseract")
        popp_ok = is_installed("pdftoppm")

        if tess_ok:
            tess_lbl.config(text="✓  TESSERACT", fg=FG_OK, font=FONT_STATUS_SIDE)
        else:
            tess_lbl.config(text="✗  TESSERACT", fg=FG_ERROR, font=FONT_STATUS_SIDE)

        if popp_ok:
            popp_lbl.config(text="POPPLER  ✓", fg=FG_OK, font=FONT_STATUS_SIDE)
        else:
            popp_lbl.config(text="POPPLER  ✗", fg=FG_ERROR, font=FONT_STATUS_SIDE)

        if tess_ok and popp_ok:
            ocr_status_lbl.config(
                text="OCR  READY", fg=FG_OK, font=FONT_STATUS_MAIN
            )
        else:
            ocr_status_lbl.config(
                text="REGEX  ONLY", fg=FG_MUTED, font=FONT_STATUS_MAIN
            )

    root.after(100, update_ocr_status)

    root.mainloop()


if __name__ == "__main__":
    run_gui()
