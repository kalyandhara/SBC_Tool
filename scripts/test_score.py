import sys
sys.path.insert(0, r'D:\SBC_Tool')
from sbc.cgsp_framework import compute_cgsp_score
from sbc.planets import positions
from datetime import datetime
import zoneinfo

# Test with Aug 30, 2026
d = "2026-08-30"
utc = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
base = datetime(2000, 1, 1, 12, 0, 0)
diff = utc - base
jul = 2451545.0 + diff.total_seconds() / 86400.0
planets, _ = positions(jul)

result = compute_cgsp_score(planets, 1)
print("=== CGSP Score Result ===")
print(f"Bias: {result['bias']}")
print(f"Net: {result['net']}")
print(f"Strength Modifier: {result['strength_modifier']}")
print(f"Market Regime: {result['market_regime']}")
print(f"Overweight Sectors: {result['overweight_sectors']}")
print()

# Test with Dec 25, 2026 (likely more bearish)
d2 = "2026-12-25"
utc2 = datetime.strptime(d2, "%Y-%m-%d").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
base2 = datetime(2000, 1, 1, 12, 0, 0)
diff2 = utc2 - base2
jul2 = 2451545.0 + diff2.total_seconds() / 86400.0
planets2, _ = positions(jul2)
result2 = compute_cgsp_score(planets2, 1)
print("=== Dec 25, 2026 ===")
print(f"Bias: {result2['bias']}")
print(f"Net: {result2['net']}")
print(f"Strength Modifier: {result2['strength_modifier']}")
print(f"Market Regime: {result2['market_regime']}")
print(f"Overweight Sectors: {result2['overweight_sectors']}")