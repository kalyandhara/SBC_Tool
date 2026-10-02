from pathlib import Path
from sbc.kota_chakra import parse_kota_excel
p = Path('C:/Users/Owner/OneDrive/Documents/Trading/SBC_Tool/data/kota/Prediction_Kota_Chakra_01.09.2026 till 15.09.2026.xlsx')
sheets = parse_kota_excel(p)
k = next(k for k in sheets if 'Dashboard' in k)
df = sheets[k]
with open('C:/Users/Owner/OneDrive/Documents/Trading/SBC_Tool/kota_out.txt','w', encoding='utf-8') as f:
    f.write('cols ' + str(list(df.columns)[:20]) + '\n')
    date_col = next((c for c in df.columns if 'Date' in str(c)), None)
    if date_col:
        f.write('date sample ' + str(df[date_col].dropna().unique()[:10].tolist()) + '\n')
        f.write('rows ' + str(len(df)) + '\n')
