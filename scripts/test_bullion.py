import sys
sys.path.insert(0, r'D:\SBC_Tool')

from sbc.bullion_vedha import scan_bullion_vedha_week, format_bullion_vedha_for_ui
import datetime

# Scan for week of Aug 24, 2026
result = scan_bullion_vedha_week(datetime.date(2026, 8, 24))
print(format_bullion_vedha_for_ui(result["daily_scans"][0]))  # Monday scan

print(f"\n\nWEEKLY SUMMARY:")
print(f"  Unique signals: {result['weekly_summary']['total_unique_signals']}")
print(f"  Gold signals: {result['weekly_summary']['gold_signals']}")
print(f"  Silver signals: {result['weekly_summary']['silver_signals']}")
print(f"  EXTREME: {result['weekly_summary']['extreme_intensity']}")
print(f"  HIGH: {result['weekly_summary']['high_intensity']}")

# Print all unique weekly signals
print("\n\nWEEKLY UNIQUE SIGNALS:")
for s in result["weekly_unique_signals"]:
    print(f"  [{s['intensity']}] {s['title']} -> {s['affected_metal']}")