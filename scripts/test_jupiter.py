import sys
sys.path.insert(0, r'D:\SBC_Tool')
from sbc.planets import positions
from datetime import datetime
import zoneinfo
import swisseph as swe

# Simple test using the existing positions() function
def test_jupiter_motion():
    # Test a few dates to see Jupiter's motion
    test_dates = [
        "2026-08-30",
        "2026-09-15", 
        "2026-12-25",
        "2026-05-01",
    ]
    
    for d in test_dates:
        try:
            utc = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata"))
            # Actually positions() takes julian day, let me use a different approach
            # Just directly check using the module's internal method
            from sbc import planets as planets_mod
            # Use the internal _julday style
            base = datetime(2000, 1, 1, 12, 0, 0)
            dt = datetime.strptime(d, "%Y-%m-%d")
            diff = dt - base
            jul = 2451545.0 + diff.total_seconds() / 86400.0
            
            planets, _ = positions(jul)
            jupiter = next(p for p in planets if p['name'] == 'Jupiter')
            print(f"{d}: speed={jupiter['speed']:.4f}, retrograde={jupiter['retrograde']}")
        except Exception as e:
            print(f"{d}: ERROR - {e}")

test_jupiter_motion()