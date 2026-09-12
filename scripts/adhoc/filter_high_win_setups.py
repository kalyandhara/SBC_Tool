import pandas as pd
confl = pd.read_csv("D:/SBC_Tool/confluence_moon_rashi_nakshatra.csv")
high = confl[confl['confidence']=='high'].copy()
# Compute win rate per rashi+nakshatra combo using actual match
combo_stats = high.groupby(['rashi','nakshatra','ruler']).agg(
    samples=('match','count'),
    wins=('match','sum')
).reset_index()
combo_stats['win_rate'] = combo_stats['wins']/combo_stats['samples']
combo_stats = combo_stats[combo_stats['samples']>=5]
# Filter combos with win_rate >0.6
good_combos = set(zip(combo_stats[combo_stats['win_rate']>0.6]['rashi'], 
                      combo_stats[combo_stats['win_rate']>0.6]['nakshatra']))
# Filter trade setups
setups = pd.read_csv("D:/SBC_Tool/moon_nakshatra_trade_setups.csv")
setups['combo'] = list(zip(setups['rashi'], setups['nakshatra']))
filtered = setups[setups['combo'].apply(lambda x: x in good_combos)]
filtered.to_csv("D:/SBC_Tool/moon_nakshatra_filtered_setups.csv", index=False)
print(f"Good combos: {len(good_combos)}")
print(f"Filtered setups: {len(filtered)}")
print(filtered['direction'].value_counts())
