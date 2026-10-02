import pandas as pd
import os

xlsx_path = r'C:\Users\Owner\Downloads\Telegram Desktop\NSEI_Nakshatra_Backtest_2011-01-01_to_2026-08-07.xlsx'
output_dir = r'C:\Users\Owner\OneDrive\Documents\Trading\SBC_Tool\Financial_Astrology\Raw\NSEI_Nakshatra_Backtest_2011-01-01_to_2026-08-07'

os.makedirs(output_dir, exist_ok=True)

xl = pd.ExcelFile(xlsx_path)
sheets = xl.sheet_names

metadata = []

for sheet in sheets:
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet)
        # Clean sheet name for filename
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in sheet).strip()
        csv_path = os.path.join(output_dir, f'{safe_name}.csv')
        df.to_csv(csv_path, index=False)
        # Also create a markdown preview with first few rows
        md_path = os.path.join(output_dir, f'{safe_name}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f'# Sheet: {sheet}\n\n')
            f.write(f'**Rows:** {len(df)}  **Columns:** {len(df.columns)}\n\n')
            f.write('**Columns:** ' + ', '.join(df.columns.astype(str)) + '\n\n')
            f.write('## Preview\n\n')
            f.write(df.head(20).to_string(index=False))
        metadata.append({
            'sheet': sheet,
            'rows': len(df),
            'cols': len(df.columns),
            'csv': f'{safe_name}.csv',
            'md': f'{safe_name}.md'
        })
        print(f'Exported {sheet} -> {safe_name}.csv ({len(df)} rows)')
    except Exception as e:
        print(f'Error exporting {sheet}: {e}')

# Create README
readme_path = os.path.join(output_dir, 'README.md')
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write('# NSEI Nakshatra Backtest 2011-01-01 to 2026-08-07\n\n')
    f.write(f'**Source:** {xlsx_path}\n\n')
    f.write(f'**Sheets exported:** {len(sheets)}\n\n')
    f.write('## Sheets\n\n')
    for m in metadata:
        f.write(f'### {m["sheet"]}\n')
        f.write(f'- Rows: {m["rows"]}, Columns: {m["cols"]}\n')
        f.write(f'- CSV: [{m["csv"]}]({m["csv"]})\n')
        f.write(f'- Preview: [{m["md"]}]({m["md"]})\n\n')
    f.write('## Files\n\n')
    for m in metadata:
        f.write(f'- [{m["csv"]}]({m["csv"]}) - raw data\n')
        f.write(f'- [{m["md"]}]({m["md"]}) - markdown preview\n')

print('Done')
