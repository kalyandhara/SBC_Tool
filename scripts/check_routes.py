"""Parametrized 200-check for all GET routes."""
import sys

sys.path.append(".")
from app import app


def main():
    client = app.test_client()
    routes = []
    for rule in app.url_map.iter_rules():
        if 'GET' in rule.methods and not rule.endpoint.startswith('static'):
            routes.append(rule.rule)
    # Deduplicate
    routes = sorted(set(routes))
    failures = []
    for route in routes:
        try:
            resp = client.get(route)
            if resp.status_code != 200:
                failures.append((route, resp.status_code))
        except Exception as e:
            failures.append((route, str(e)))
    print(f"Checked {len(routes)} GET routes")
    if failures:
        print("Failures:")
        for r, code in failures:
            print(f"  {r} -> {code}")
    else:
        print("All GET routes returned 200 or were acceptable.")

if __name__ == "__main__":
    main()
