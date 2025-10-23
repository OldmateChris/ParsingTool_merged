from __future__ import annotations
import re
from typing import List, Dict

from ..shared.pdf_utils import extract_text
from ..shared.text_utils import lines, find_first, take_around
from ..shared.date_utils import to_ddmmyyyy
from ..shared.csv_writer import write_csv
from ..shared.schemas import BATCHES_COLUMNS, SSCC_COLUMNS

# -----------------------------
# Header label patterns (kept readable & forgiving)
# -----------------------------
HEADER_PATTERNS = {
    "delivery": r"\bDelivery\s+([0-9]{6,})\b",
    "picking": r"\bPicking\s*request\s*([0-9]{6,})\b",
    "olam": r"\bOlam\s*Reference\s*([0-9A-Z-/]+)\b",
    "customer_delivery_date": r"\bCustomer\s*Delivery\s*Date\s*([0-9./-]{8,10})\b",
    "plant_storage": r"\bPlant/Storage\s*location\s*([A-Z0-9/]+)\b",
    "gross_weight": r"\bGross\s*weight\s*([0-9.,]+)\s*KG\b",
}

# -----------------------------
# Batch/SSCC/product patterns (fine-tuned per your PDFs)
# -----------------------------
BATCH_RE = re.compile(r"\b(F\d{6,})\b", re.IGNORECASE)
PAL_RE = re.compile(r"\b(\d+)\s*PAL\b", re.IGNORECASE)
SSCC_RE = re.compile(r"\b(\d{18,20})\b")  # 18-20 digit codes
SIZE_RE = re.compile(r"\b(\d{2}/\d{2})\b")

# Packaging patterns to cover: "12.5KG ctn", "1T bag", "850KG D-Sp", etc.
# We capture a number + unit (KG or T) plus an optional packaging word.
PACK_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(KG|T)\b\s*(?:([A-Za-z-]{2,6}))?",
    re.IGNORECASE,
)

# Grade tokens: include SSR, Supr (case-insensitive), and allow 2-4 uppercase letters as fallback.
# Normalised names we will emit when we detect a match
KNOWN_GRADES = [
    "SSR",
    "Supr",
    "XNo1",
]
# Broad fallback (after trying explicit patterns) — keeps previous behaviour for 2–4 letter codes
GRADE_TOKEN_RE = re.compile(r"\b([A-Z]{2,4})\b")


# -----------------------------
# Header parsing
# -----------------------------

def _parse_headers(text: str) -> Dict[str, str]:
    h: Dict[str, str] = {}
    h["Delivery Number"] = find_first(HEADER_PATTERNS["delivery"], text)
    h["Picking Request Number"] = find_first(HEADER_PATTERNS["picking"], text)
    h["OLAM Ref Number"] = find_first(HEADER_PATTERNS["olam"], text)

    dt_raw = find_first(HEADER_PATTERNS["customer_delivery_date"], text)
    h["Customer Delivery Date"] = to_ddmmyyyy(dt_raw)

    h["Plant/Storage Location"] = find_first(HEADER_PATTERNS["plant_storage"], text)

    gw = find_first(HEADER_PATTERNS["gross_weight"], text)
    h["Total Gross Weight"] = gw.replace(",", "") if gw else ""

    # Customer + Address heuristic: find a likely customer line (Pty/Ltd etc.)
    # then capture a few lines after it until a known label appears.
    all_lines = lines(text)
    customer = ""
    address_parts: List[str] = []
    for i, ln in enumerate(all_lines):
        if re.search(r"\b(Pty|Limited|Ltd|Pty Ltd|Pty\.|Ltd\.)\b", ln):
            customer = ln.strip()
            for follow in take_around(i + 1, all_lines, before=0, after=4):
                if re.search(r"(Delivery|Olam|Picking|Plant/Storage|Gross\s*weight)", follow, re.IGNORECASE):
                    break
                if follow:
                    address_parts.append(follow)
            break
    h["Customer"] = customer
    h["Customer/Delivery Address"] = ", ".join(address_parts)
    return h


# -----------------------------
# Batch blocks + SSCC collection
# -----------------------------

def _parse_batches_and_sscc(text: str) -> List[dict]:
    """Return a list of dict blocks with: Batch_Number, pal_text, sscc_list, product_lines."""
    ls = lines(text)
    blocks: List[dict] = []

    for idx, ln in enumerate(ls):
        m = BATCH_RE.search(ln)
        if not m:
            continue
        batch = m.group(1)

        # X PAL on same or nearby lines
        pal_text = ""
        m_pal = PAL_RE.search(ln)
        if not m_pal:
            for near in take_around(idx, ls, before=0, after=3):
                m_pal = PAL_RE.search(near)
                if m_pal:
                    break
        if m_pal:
            pal_text = f"{m_pal.group(1)} PAL"

        # Collect subsequent lines until next batch or a reasonable window
        ssccs: List[str] = []
        product_lines: List[str] = []
        for j in range(idx + 1, min(idx + 60, len(ls))):
            nxt = ls[j]
            if BATCH_RE.search(nxt):
                break
            # SSCCs may appear with or without an 'SSCC:' label
            for mss in SSCC_RE.finditer(nxt):
                ssccs.append(mss.group(1))
            # Keep candidate product lines: ones containing size/pack/grade tokens
            if SIZE_RE.search(nxt) or PACK_RE.search(nxt) or GRADE_TOKEN_RE.search(nxt):
                product_lines.append(nxt)

        blocks.append({
            "Batch_Number": batch,
            "pal_text": pal_text,
            "sscc_list": ssccs,
            "product_lines": product_lines[-4:],  # last few are usually closest to batch
        })

    return blocks


# -----------------------------
# Product field extraction (Variety / Grade / Size / Packaging)
# -----------------------------

def _parse_product_fields(product_lines: List[str]) -> dict:
    txt = " ".join(product_lines)

    # Size
    size = ""
    ms = SIZE_RE.search(txt)
    if ms:
        size = ms.group(1)

    # Packaging
    packaging = ""
    mp = PACK_RE.search(txt)
    if mp:
        num, unit, word = mp.groups()
        unit = unit.upper()
        word = (word or "").lower()
        # Normalise unit to 'KG' or 'T'
        if unit not in {"KG", "T"}:
            unit = "KG"
        # Normalise common packaging tokens
        synonyms = {
            "ctn": "ctn",
            "bag": "bag",
            "case": "case",
            "carton": "ctn",
            "d-sp": "D-Sp",
            "dsp": "D-Sp",
            "t": "bag",  # e.g., "1T" (we'll show it as "1T bag" if no word)
        }
        norm_word = synonyms.get(word, word)
        if unit == "T" and not norm_word:
            # e.g., "1T" often implies a big bag; keep as '1T bag'
            norm_word = "bag"
        # Build final text (preserve number decimals)
        packaging = f"{num}{unit} {norm_word}".strip()

    # Grade (prefer known tokens; fallback to 2–4 uppercase letters)
    grade = ""
    # Try explicit patterns first (case-insensitive)
    grade_patterns = [
        (r"\bSSR\b", "SSR"),
        (r"\bSUPR\b", "Supr"),   # normalise to 'Supr'
        (r"\bSupr\b", "Supr"),
        # XNo1 forms: XNO1, X No1, X No.1, Xno1
        (r"\bX\s*NO\.?\s*1\b", "XNo1"),
        (r"\bXNO1\b", "XNo1"),
        (r"\bXno1\b", "XNo1"),
    ]
    for pat, norm in grade_patterns:
        if re.search(pat, txt, flags=re.IGNORECASE):
            grade = norm
            break
    if not grade:
        mg = GRADE_TOKEN_RE.search(txt)
        if mg:
            grade = mg.group(1)

    # Variety – take text before the grade token if present; else before size/pack
    variety = ""
    split_anchor = grade or (ms.group(0) if ms else "") or (mp.group(0) if mp else "")
    if split_anchor:
        parts = txt.split(split_anchor, 1)[0].strip()
        variety = re.sub(r"\s+", " ", parts)

    return {
        "Variety": variety,
        "Grade": grade,
        "Size": size,
        "Packaging": packaging,
    }

# -----------------------------
# Public entrypoint
# -----------------------------

def run(*, input_pdf: str, out_batches: str, out_sscc: str) -> None:
    # 1) Extract text
    text = extract_text(input_pdf)

    # 2) Headers
    H = _parse_headers(text)

    # 3) Batches & SSCC blocks
    blocks = _parse_batches_and_sscc(text)

    # 4) Build rows
    batch_rows: List[Dict[str, str]] = []
    sscc_rows: List[Dict[str, str]] = []

    for b in blocks:
        prod = _parse_product_fields(b.get("product_lines", []))
        ssccs = b.get("sscc_list", [])

        # SSCC Qty rule: only set "X PAL" if matches count
        pal_txt = b.get("pal_text", "")
        sscc_qty = ""
        if pal_txt:
            m = re.search(r"(\d+)\s*PAL", pal_txt, flags=re.IGNORECASE)
            if m and len(ssccs) == int(m.group(1)):
                sscc_qty = f"{m.group(1)} PAL"

        # Batch row (all columns present; many intentionally blank for override later)
        row = {
            "Requested By": "",
            "Date Requested": "",
            "Picking Request Number": H.get("Picking Request Number", ""),
            "Delivery Number": H.get("Delivery Number", ""),
            "OLAM Ref Number": H.get("OLAM Ref Number", ""),
            "Batch Number": b.get("Batch_Number", ""),
            "SSCC Qty": sscc_qty,
            "Customer Delivery Date": H.get("Customer Delivery Date", ""),
            "Customer": H.get("Customer", ""),
            "Customer/Delivery Address": H.get("Customer/Delivery Address", ""),
            "Date of Pick Up": "",
            "Total Days In Transit": "",
            "Plant/Storage Location": H.get("Plant/Storage Location", ""),
            "Inspection Type": "",
            "Inspection progress": "",
            "Inspection Status": "",
            "Inspection Date": "",
            "Variety": prod.get("Variety", ""),
            "Grade": prod.get("Grade", ""),
            "Size": prod.get("Size", ""),
            "Packaging": prod.get("Packaging", ""),
            "Total Gross Weight": H.get("Total Gross Weight", ""),
            "Pallet": "",  # always blank
            "Comments": "",
            "Non-Conformance": "",
        }
        batch_rows.append(row)

        # SSCC detail rows
        for ss in ssccs:
            sscc_rows.append({
                "Delivery Number": H.get("Delivery Number", ""),
                "Batch Number": b.get("Batch_Number", ""),
                "SSCC": ss,
                "Variety": prod.get("Variety", ""),
                "Grade": prod.get("Grade", ""),
                "Size": prod.get("Size", ""),
                "Packaging": prod.get("Packaging", ""),
            })

    # 5) Write CSVs
    write_csv(out_batches, batch_rows, BATCHES_COLUMNS)
    write_csv(out_sscc, sscc_rows, SSCC_COLUMNS)
