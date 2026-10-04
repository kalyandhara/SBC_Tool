"""B-14: GeoNames city seed and search."""

import io
import zipfile

import pytest

from sbc import cities


def _row(gid, name, ascii_name, lat, lon, cc, admin1, pop, tz):
    cols = [str(gid), name, ascii_name, "", str(lat), str(lon), "P", "PPL", cc, "", admin1,
            "", "", "", str(pop), "", "", tz, "2024-01-01"]
    return "\t".join(cols)


@pytest.fixture
def db(tmp_path):
    src = tmp_path / "geonames"
    src.mkdir()
    rows = [
        _row(1, "Delhi Cantonment", "Delhi Cantonment", 28.6, 77.1, "IN", "07", 110351, "Asia/Kolkata"),
        _row(2, "Delhi", "Delhi", 28.65, 77.23, "IN", "07", 11034555, "Asia/Kolkata"),
        _row(3, "New Delhi", "New Delhi", 28.61, 77.21, "IN", "07", 317797, "Asia/Kolkata"),
        _row(4, "Āmta", "Amta", 22.57, 88.02, "IN", "28", 16753, "Asia/Kolkata"),
        _row(5, "Delhi", "Delhi", 42.28, -74.92, "US", "NY", 20000, "America/New_York"),
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("cities15000.txt", "\n".join(rows) + "\n")
    (src / "cities15000.zip").write_bytes(buf.getvalue())
    (src / "countryInfo.txt").write_text(
        "#ISO\tISO3\tISO-Numeric\tfips\tCountry\n"
        "IN\tIND\t356\tIN\tIndia\nUS\tUSA\t840\tUS\tUnited States\n", encoding="utf-8")
    (src / "admin1CodesASCII.txt").write_text(
        "IN.07\tDelhi\tDelhi\t1\nIN.28\tWest Bengal\tWest Bengal\t2\nUS.NY\tNew York\tNew York\t3\n",
        encoding="utf-8")
    path = tmp_path / "cities.db"
    assert cities.build(src, path) == 5
    return path


def test_exact_then_prefix_then_substring(db):
    names = [(r["name"], r["country"]) for r in cities.search("delhi", db_path=db)]
    assert names[:2] == [("Delhi", "India"), ("Delhi", "United States")]
    assert names[2:] == [("Delhi Cantonment", "India"), ("New Delhi", "India")]  # prefix before substring


def test_ascii_names_admin_and_timezone(db):
    r = cities.search("Amta", db_path=db)[0]
    assert r["name"] == "Āmta" and r["admin"] == "West Bengal" and r["timezone"] == "Asia/Kolkata"


def test_country_filters_and_limits(db):
    assert {r["country"] for r in cities.search("delhi", "USA", db_path=db)} == {"United States"}
    assert {r["country"] for r in cities.search("delhi", "IN", db_path=db)} == {"India"}
    assert len(cities.search("delhi", limit=1, db_path=db)) == 1
    assert cities.search("d", db_path=db) == []
    assert cities.search("%", db_path=db) == []


def test_endpoint(client, db, monkeypatch):
    monkeypatch.setattr(cities, "DB_PATH", db)
    body = client.get("/api/cities/search?q=delhi&limit=2").get_json()
    assert [r["name"] for r in body] == ["Delhi", "Delhi"] and "lat" in body[0]
    assert client.get("/api/cities/search?q=delhi&limit=x").status_code == 400
    assert client.get("/api/cities/search?q=d").get_json() == []
