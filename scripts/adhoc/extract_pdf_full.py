import sys
from PyPDF2 import PdfReader
path = r"D:\K.N. Rao - Planets & Children (Vedic Astrology Series) (1993, S. Kumar and Associates) - libgen.li.pdf"
reader = PdfReader(path)
out_path = r"C:\Users\Owner\OneDrive\Documents\Trading\SBC_Tool\kn_rao_planets_children.txt"
with open(out_path, 'w', encoding='utf-8') as f:
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        f.write(f"\n--- Page {i+1} ---\n")
        f.write(txt)
print(f"Extracted {len(reader.pages)} pages to {out_path}")
