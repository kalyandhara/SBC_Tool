"""Read the newest validation reports in docs/research/ (written by scripts/validate_*.py).

The forecast attaches each component's verdict from these reports, so the
verdicts update when the reports are regenerated, without a code change.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "docs" / "research"
PREFIXES = ("rule_validation", "analog_validation", "incremental_validation", "factor_validation",
            "sector_validation", "swing_validation", "natal_validation")


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> dict:
    report: dict = json.loads(Path(path).read_text(encoding="utf-8"))
    return report


def latest(prefix: str) -> dict | None:
    """Newest `<prefix>_<date>.json` as a dict (with its file name under "_file"), or None."""
    reports = sorted(REPORT_DIR.glob(f"{prefix}_*.json"))
    if not reports:
        return None
    path = reports[-1]
    return {**_load(str(path), path.stat().st_mtime), "_file": path.name}


def result(prefix: str, rule: str, horizon: int) -> dict | None:
    """One rule's row for one horizon from the newest report of that kind."""
    report = latest(prefix)
    if not report:
        return None
    for r in report["results"]:
        if r["rule"] == rule and r["horizon"] == horizon:
            return {**r, "_file": report["_file"], "_sample": report.get("sample")}
    return None


def counts() -> dict:
    """Per report kind: how many tests it ran and how many passed (edge / adds information)."""
    out = {}
    for prefix in PREFIXES:
        report = latest(prefix)
        if not report:
            continue
        verdicts = [r.get("verdict") for r in report["results"]]
        positive = "adds information" if prefix == "incremental_validation" else "edge"
        out[prefix] = {"tests": len(verdicts), "passed": verdicts.count(positive), "report": report["_file"]}
    return out
