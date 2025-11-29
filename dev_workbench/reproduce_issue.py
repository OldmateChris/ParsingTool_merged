from ParsingTool.parsing.shared.pdf_utils import extract_text
import re

text = extract_text('input/export_sample.pdf')
FLAGS = re.IGNORECASE | re.MULTILINE

print("--- TEXT AROUND PACKER ---")
m_context = re.search(r"(.{0,50})(Packer\s*:\s*\n.{0,100})", text, re.DOTALL | re.IGNORECASE)
if m_context:
    print(f"'{m_context.group(0)}'")
else:
    print("Context not found")

print("\n--- CURRENT REGEX MATCH ---")
m = re.search(r"Packer\s*:\s*\n([^\n]+)", text, FLAGS)
if m:
    print(f"Group 1: '{m.group(1)}'")
else:
    print("No match")

print("\n--- TEST NEW REGEX ---")
# Try capturing multiple lines if needed
m2 = re.search(r"Packer\s*:\s*\n([^\n]+(?:\n[^\n]+)?)", text, FLAGS)
if m2:
    print(f"Group 1 (multiline): '{m2.group(1)}'")
