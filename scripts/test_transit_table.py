import sys
sys.path.insert(0, r'D:\SBC_Tool')
from sbc.cgsp_framework import get_jupiter_transit_table

table = get_jupiter_transit_table()
for entry in table:
    print(f"{entry['sign']:12s}: Direct={entry['direct']:8s} Retrograde={entry['retrograde']:8s}")