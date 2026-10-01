import sys
path = r"D:\K.N. Rao - Planets & Children (Vedic Astrology Series) (1993, S. Kumar and Associates) - libgen.li.pdf"
try:
    from PyPDF2 import PdfReader
    reader = PdfReader(path)
    text = ""
    for i, page in enumerate(reader.pages[:5]):
        text += f"\n--- Page {i+1} ---\n" + page.extract_text() or ""
    print(text[:4000])
    print(f"\nTotal pages: {len(reader.pages)}")
except Exception as e:
    print("Error:", e)
