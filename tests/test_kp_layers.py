"""v15 layers of the KP intraday report: Nadi, Navamsa, A-13 windows, DOCX export."""

import datetime
import io
import re
import zipfile
from pathlib import Path

import pytest

from sbc import kp_layers as L


def test_sapta_nadi_covers_all_28_stars_once():
    seen = [n for naks in L.SAPTA_NADI.values() for n in naks]
    assert len(seen) == 28
    assert len(set(seen)) == 28
    assert L.NADI_OF_NAKSHATRA["Punarvasu"] == "Neer"      # matches the reference report
    assert L.NADI_PROFILE["Neer"][0] == 1.05


def test_normalize_kp_spellings():
    assert L.normalize_nakshatra("Purva Ashadha") == "P.Ashadha"
    assert L.normalize_nakshatra("Uttara Phalguni") == "U.Phalguni"
    assert L.normalize_nakshatra("Ashvini") == "Ashwini"
    assert L.normalize_nakshatra("Punarvasu") == "Punarvasu"


def test_navamsa_math_and_vargottama():
    # 0-3°20' Aries -> Aries navamsa (vargottama)
    n = L.navamsa_of(1.0)
    assert (n.d1_sign, n.d9_sign, n.vargottama) == ("Aries", "Aries", True)
    # Cancer 0-3°20' -> Cancer (water signs start their navamsas at Cancer)
    n = L.navamsa_of(91.0)
    assert (n.d1_sign, n.d9_sign, n.vargottama) == ("Cancer", "Cancer", True)
    # Aries 7th navamsa (20°-23°20') -> Libra, pushkara for fire signs
    n = L.navamsa_of(21.0)
    assert n.d9_sign == "Libra" and n.pushkara_navamsa and n.pushkara_bhaga


def test_dignity_table():
    assert L.dignity("Ketu", "Taurus") == "debilitated"     # reference: Ketu -> Taurus (debilitated)
    assert L.dignity("Moon", "Gemini") == "friend"          # reference: Moon -> Gemini (friend)
    assert L.dignity("Mars", "Aries") == "own"
    assert L.dignity("Mercury", "Sagittarius") == "neutral"


def test_rahu_windows_from_rows():
    rows = [
        {"timestamp": f"2026-09-07T{h:02d}:{m:02d}:00", "planet": "Moon",
         "sublord": "Rahu" if (h, m) >= (14, 45) else "Mars"}
        for h in range(9, 16) for m in (0, 15, 30, 45) if (9, 15) <= (h, m) <= (15, 30)
    ]
    assert L.rahu_moon_sub_windows(rows) == [("14:45", "15:30")]
    assert "14:45 to 15:30" in L.rahu_windows_text(L.rahu_moon_sub_windows(rows))


def test_incoming_sublord_parse():
    assert L.incoming_sublord_from_trigger("Asc sub change Saturn->Mercury") == "Mercury"
    assert L.incoming_sublord_from_trigger("Moon sub change Sun->Moon; Asc sub change Mars->Rahu") == "Moon"
    assert L.incoming_sublord_from_trigger("") == ""


@pytest.mark.skipif(not Path("data/kp/KP_Data_Sep2026.csv").exists(), reason="needs the Sep-2026 KP file")
def test_report_carries_v15_layers_and_exports_docx():
    from sbc.kp_config import get_config, get_instrument_config
    from sbc.kp_docx import render_docx
    from sbc.kp_intraday import generate_kp_intraday_report

    cfg = get_instrument_config("NIFTY", get_config())
    rep = generate_kp_intraday_report(Path("data/kp/KP_Data_Sep2026.csv"), datetime.date(2026, 9, 7), "NIFTY", cfg)
    ds = rep.day_signature
    assert ds.rahu_windows_note.startswith("Rahu Moon-sub windows (Rule A-13)")
    assert ds.vargottama_note.startswith("Vargottama Moon (Rule C-5)")
    assert ds.navamsa and "error" not in ds.navamsa and ds.navamsa["placements"]
    assert ds.nadi and ds.nadi["nadi"] in L.NADI_PROFILE
    assert all(tc.nadi for tc in rep.trend_changes)

    body = render_docx(rep)
    assert body[:2] == b"PK"
    text = re.sub(r"<[^>]+>", " ", zipfile.ZipFile(io.BytesIO(body)).read("word/document.xml").decode("utf8", "ignore"))
    for heading in ("1. Day Chart Signature", "1b. Navamsa (D-9) Strength Layer (v15)",
                    "1c. SBC Nadi Classification (v15.1)", "2. Master Regime Shifts",
                    "4. Trend Change Timing Table", "5. Intraday Trading View", "6. Disclaimer"):
        assert heading in text, heading


def test_docx_route(client):
    resp = client.get("/api/kp_intraday_report?date=2026-09-07&instrument=NIFTY&format=docx")
    assert resp.status_code == 200
    assert resp.mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert resp.headers["Content-Disposition"].endswith('KP_Intraday_Prediction_Report_2026-09-07.docx')
    assert resp.data[:2] == b"PK"
