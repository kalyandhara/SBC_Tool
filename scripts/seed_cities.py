"""Build data/cities.db from GeoNames (cities with population >= 15,000).

  python scripts/seed_cities.py              # download into data/geonames/ if missing, then build
  python scripts/seed_cities.py --refresh    # re-download the GeoNames files first
  python scripts/seed_cities.py --offline    # build from files already in data/geonames/

Data: GeoNames (https://www.geonames.org/), CC BY 4.0. About 3.5 MB to download.
"""

import argparse
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import cities  # noqa: E402

SOURCE_DIR = cities.ROOT / "data" / "geonames"


def download(refresh: bool) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for name in cities.FILES:
        target = SOURCE_DIR / name
        if target.exists() and not refresh:
            continue
        url = cities.GEONAMES_BASE + name
        print(f"downloading {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "SBC-Tool city seed"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        tmp = target.with_suffix(target.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        print(f"  {len(data) / 1024:.0f} KB -> {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="re-download the GeoNames files")
    parser.add_argument("--offline", action="store_true", help="don't download; use data/geonames/")
    args = parser.parse_args()
    if not args.offline:
        download(args.refresh)
    t0 = time.perf_counter()
    n = cities.build(SOURCE_DIR)
    print(f"wrote {n} cities to {cities.DB_PATH} in {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
