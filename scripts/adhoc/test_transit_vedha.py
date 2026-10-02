import sys

sys.path.insert(0, r'D:\SBC_Tool')

import datetime

from sbc.transit_vedha import (
    format_transit_vedha_for_ui,
    scan_transit_vedha_matrix,
    scan_transit_vedha_week,
)

# Test for Aug 24, 2026
result = scan_transit_vedha_matrix(datetime.date(2026, 8, 24))
print(format_transit_vedha_for_ui(result))

print("\n\nWEEKLY:")
weekly = scan_transit_vedha_week(datetime.date(2026, 8, 24))
print(f"  Unique signals: {weekly['weekly_summary']['total_unique_signals']}")
print(f"  EXTREME: {weekly['weekly_summary']['extreme_count']}")
print(f"  HIGH: {weekly['weekly_summary']['high_count']}")
print(f"  Sectors: {weekly['weekly_summary']['sectors_activated']}")
print("\nSector Summary:")
for sector, info in weekly['weekly_sector_summary'].items():
    print(f"  {sector}: {info['count']} signals, max {info['max_intensity']}")
