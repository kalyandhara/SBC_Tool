#!/usr/bin/env python3
"""CLI for B-47 third-party monthly score rebuild, gated on B-40 verdict."""

import argparse
import sys
sys.path.insert(0, r'C:\Users\Owner\OneDrive\Documents\Trading\SBC_Tool')

from sbc.third_party_rebuild import fit_monthly_weights, ENABLED

def main():
    p = argparse.ArgumentParser(description="B-47 rebuild third-party monthly score")
    p.add_argument("--month", required=True, help="YYYY-MM")
    p.add_argument("--source", default="third_party_monthly")
    args = p.parse_args()

    if not ENABLED:
        print(f"B-47 is gated. ENABLED=False. Run B-40 scoring first.")
        print("Set ENABLED=True in sbc/third_party_rebuild.py after verdict shows edge.")
        sys.exit(1)

    res = fit_monthly_weights(args.month, args.source)
    print(res)

if __name__ == "__main__":
    main()
