import re
from pathlib import Path

text = Path('debug_text.txt').read_text(encoding='utf-8')
FLAGS = re.IGNORECASE | re.MULTILINE

print("--- SEARCHING ---")

desc_match = None

# 1. Primary
if not desc_match:
    m = re.search(r"(Almonds[^\n]+)", text, FLAGS)
    if m:
        print(f"Matched Primary: '{m.group(1)}'")
        desc_match = m

# 2. Fallback
if not desc_match:
    m = re.search(r"((?:A[lI]monds|Kern|\bALM\b)[^\n]+)", text, FLAGS)
    if m:
        print(f"Matched Fallback: '{m.group(1)}'")
        desc_match = m

# 3. Fallback Context
if not desc_match:
    m = re.search(r"([^\n]*\d{2}\s*/\s*\d{2}[^\n]*)", text, FLAGS)
    if m:
        print(f"Matched Context: '{m.group(1)}'")
        desc_match = m

# 4. Fallback Keywords
if not desc_match:
    m = re.search(r"((?:Stockfeed|Mfr|Manufacturing|Inshell|Hulls)[^\n]+)", text, FLAGS)
    if m:
        print(f"Matched Keywords: '{m.group(1)}'")
        desc_match = m

if not desc_match:
    print("NO MATCH FOUND")
