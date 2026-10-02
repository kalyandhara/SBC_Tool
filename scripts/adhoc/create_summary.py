import pandas as pd
import os

base_dir = r'C:\Users\Owner\OneDrive\Documents\Trading\SBC_Tool\Financial_Astrology\Raw\NSEI_Nakshatra_Backtest_2011-01-01_to_2026-08-07'

params = pd.read_csv(os.path.join(base_dir, 'Parameters.csv'))
sum_open = pd.read_csv(os.path.join(base_dir, 'Sum_OpenNak.csv'))
sum_close = pd.read_csv(os.path.join(base_dir, 'Sum_CloseNak.csv'))
sum_open_pada = pd.read_csv(os.path.join(base_dir, 'Sum_OpenNak_Pada.csv'))
sum_close_pada = pd.read_csv(os.path.join(base_dir, 'Sum_CloseNak_Pada.csv'))
sum_stable = pd.read_csv(os.path.join(base_dir, 'Sum_StableOnly.csv'))
gap_summary = pd.read_csv(os.path.join(base_dir, 'GapUp_Summary.csv'))

def dict_from_params(df):
    return dict(zip(df['Parameter'], df['Value']))

pdict = dict_from_params(params)

# Key metrics
best_open = sum_open.loc[sum_open['Avg DoD %'].idxmax()]
worst_open = sum_open.loc[sum_open['Avg DoD %'].idxmin()]
best_close = sum_close.loc[sum_close['Avg DoD %'].idxmax()]
worst_close = sum_close.loc[sum_close['Avg DoD %'].idxmin()]

# Bias counts
bias_counts_open = sum_open['Bias'].value_counts().to_dict()
bias_counts_close = sum_close['Bias'].value_counts().to_dict()

# Significant counts
sig_open = sum_open['Significant'].value_counts().to_dict()
sig_close = sum_close['Significant'].value_counts().to_dict()

# Pad best
best_pada_open = sum_open_pada.loc[sum_open_pada['Avg DoD %'].idxmax()]
worst_pada_open = sum_open_pada.loc[sum_open_pada['Avg DoD %'].idxmin()]

lines = []
lines.append('# NSEI Nakshatra Backtest – Consolidated Summary')
lines.append('')
lines.append('## Backtest Parameters')
lines.append('')
for k,v in pdict.items():
    lines.append(f'- **{k}:** {v}')
lines.append('')

lines.append('## Overview')
lines.append(f'- Total Sessions: {pdict.get("Total Sessions","-")}')
lines.append(f'- Stable Sessions: {pdict.get("Stable Sessions","-")}')
lines.append(f'- Pada Transit Sessions: {pdict.get("Pada Transit Sessions","-")}')
lines.append(f'- Nakshatra Transit Sessions: {pdict.get("Nakshatra Transit Sessions","-")}')
lines.append(f'- Gap Up Instances >=0.5%: {pdict.get("Gap Up Instances","-")}')
lines.append('')

lines.append('## Open Nakshatra Summary')
lines.append(f'- Nakshatras analysed: {len(sum_open)}')
lines.append(f'- Best Avg DoD % on Open: {best_open["Open_Nakshatra"]} = {best_open["Avg DoD %"]:.3f}%  Total Days {best_open["Total Days"]}')
lines.append(f'- Worst Avg DoD % on Open: {worst_open["Open_Nakshatra"]} = {worst_open["Avg DoD %"]:.3f}%  Total Days {worst_open["Total Days"]}')
lines.append(f'- Bias distribution: {bias_counts_open}')
lines.append(f'- Significant flags: {sig_open}')
lines.append('')

lines.append('## Close Nakshatra Summary')
lines.append(f'- Nakshatras analysed: {len(sum_close)}')
lines.append(f'- Best Avg DoD % on Close: {best_close["Close_Nakshatra"]} = {best_close["Avg DoD %"]:.3f}%  Total Days {best_close["Total Days"]}')
lines.append(f'- Worst Avg DoD % on Close: {worst_close["Close_Nakshatra"]} = {worst_close["Avg DoD %"]:.3f}%  Total Days {worst_close["Total Days"]}')
lines.append(f'- Bias distribution: {bias_counts_close}')
lines.append(f'- Significant flags: {sig_close}')
lines.append('')

lines.append('## Pada Level Highlights')
lines.append(f'- Pada rows analysed: {len(sum_open_pada)}')
lines.append(f'- Best Avg DoD % on Open Pada: {best_pada_open["Open_Nakshatra"]} Pada {best_pada_open.get("Open_Pada","-")} = {best_pada_open["Avg DoD %"]:.3f}%')
lines.append(f'- Worst Avg DoD % on Open Pada: {worst_pada_open["Open_Nakshatra"]} Pada {worst_pada_open.get("Open_Pada","-")} = {worst_pada_open["Avg DoD %"]:.3f}%')
lines.append('')

lines.append('## Gap Up Summary')
lines.append(f'- Gap up rows: {len(gap_summary)}')
if 'Avg Gap %' in gap_summary.columns:
    top_gap = gap_summary.nlargest(5, 'Avg Gap %')
    lines.append('- Top 5 Nakshatras by Avg Gap %:')
    for _, row in top_gap.iterrows():
        lines.append(f'  - {row.get("Open_Nakshatra","-")} : {row.get("Avg Gap %","-"):.3f}%  GapUp>=0.5% {row.get("GapUp>=0.5%","-")}')
lines.append('')

lines.append('## Files Reference')
lines.append('- Parameters.csv, Sum_OpenNak.csv, Sum_CloseNak.csv, Sum_OpenNak_Pada.csv, Sum_CloseNak_Pada.csv, Sum_StableOnly.csv, GapUp_Summary.csv, GapUp_Detail.csv, Daily_Raw.csv')
lines.append('')

summary_path = os.path.join(base_dir, 'CONSOLIDATED_SUMMARY.md')
with open(summary_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('Summary written to', summary_path)
