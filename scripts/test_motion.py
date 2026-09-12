import sys
sys.path.insert(0, r'D:\SBC_Tool')
from sbc.cgsp_framework import get_jupiter_motion
from sbc.planets import positions
from datetime import datetime
import zoneinfo

# Test with Aug 30, 2026 (Jupiter direct)
d = "2026-08-30"
utc = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
base = datetime(2000, 1, 1, 12, 0, 0)
diff = utc - base
jul = 2451545.0 + diff.total_seconds() / 86400.0
planets, _ = positions(jul)
motion = get_jupiter_motion(planets)
print(f"{d}: Jupiter motion = {motion}")

# Test with Dec 25, 2026 (Jupiter retrograde)
d2 = "2026-12-25"
utc2 = datetime.strptime(d2, "%Y-%m-%d").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
base2 = datetime(2000, 1, 1, 12, 0, 0)
diff2 = utc2 - base2
jul2 = 2451545.0 + diff2.total_seconds() / 86400.0
planets2, _ = positions(jul2)
motion2 = get_jupiter_motion(planets2)
print(f"{d2}: Jupiter motion = {motion2}")

# Test with May 1, 2026 (Jupiter direct)
d3 = "2026-05-01"
utc3 = datetime.strptime(d3, "%Y-%m-%d").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
base3 = datetime(2000, 1, 1, 12, 0, 0)
diff3 = utc3 - base3
jul3 = 2451545.0 + diff3.total_seconds() / 86400.0
planets3, _ = positions(jul3)
motion3 = get_jupiter_motion(planets3)
print(f"{d3}: Jupiter motion = {motion3}")