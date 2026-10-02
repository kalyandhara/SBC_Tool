"""
Exporters for CSV/XLSX with metadata.
"""
import csv
from pathlib import Path

import pandas as pd


def export_csv(rows, out_path, fieldnames):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def export_xlsx(df, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path) as writer:
        df.to_excel(writer, index=False, sheet_name="data")
