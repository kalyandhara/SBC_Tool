"""Backtest the app against the pasted Saturn-in-Taurus view.
The view claims: Saturn in Taurus (bearish), exits to Aries (bullish), 2029-2030 crash.
Check what the app actually predicts for relevant periods."""
from sbc.backtest import run_bearish_futurecast, run_bullish_futurecast

# Current date (2026) - Saturn in Pisces
print("=== BEARISH FUTURECAST from 2026 (Saturn in Pisces) ===")
result = run_bearish_futurecast(center_date="2026-08-25", years=5)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")

print("\n=== BULLISH FUTURECAST from 2026 ===")
result = run_bullish_futurecast(center_date="2026-08-25", years=5)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")

# 2029-2030 period - Saturn enters Taurus Aug 2029
print("\n=== BEARISH FUTURECAST from 2029-08-15 (Saturn enters Taurus) ===")
result = run_bearish_futurecast(center_date="2029-08-15", years=2)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")

print("\n=== BULLISH FUTURECAST from 2029-08-15 ===")
result = run_bullish_futurecast(center_date="2029-08-15", years=2)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")

# 2030-2031 period - Saturn in Taurus
print("\n=== BEARISH FUTURECAST from 2030-04-17 (Saturn firmly in Taurus) ===")
result = run_bearish_futurecast(center_date="2030-04-17", years=2)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")

# Saturn moves to Aries 2027 (briefly) then 2028 - the "bull phase" per the view
print("\n=== BULLISH FUTURECAST from 2027-06-09 (Saturn enters Aries) ===")
result = run_bullish_futurecast(center_date="2027-06-09", years=2)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")

print("\n=== BEARISH FUTURECAST from 2027-06-09 ===")
result = run_bearish_futurecast(center_date="2027-06-09", years=2)
for c in result.get("clusters", []):
    print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {c['triggers']}")
