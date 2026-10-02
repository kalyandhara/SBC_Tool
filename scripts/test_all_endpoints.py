import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test all endpoints with empty date
    endpoints = [
        '/api/futurecast?date=',
        '/api/bullish_futurecast?date=',
        '/api/bearish_futurecast?date=',
        '/api/weekly_commentary?date=',
        '/api/bullion_vedha?date=',
        '/api/bullion_vedha_week?date=',
        '/api/transit_vedha?date=',
        '/api/transit_vedha_week?date=',
        '/api/astro_plot?date=',
        '/api/prediction?date=',
        '/api/crash_analysis?date=',
    ]

    for ep in endpoints:
        resp = client.get(ep)
        status = "OK" if resp.status_code == 200 else f"FAIL ({resp.status_code})"
        print(f"{ep}: {status}")
        if resp.status_code != 200:
            print(f"  Error: {resp.get_data(as_text=True)[:200]}")

    print("\nAll endpoints tested!")
