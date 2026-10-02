"""The 9x9 Sarvatobhadra Chakra grid and its vedha (piercing) geometry.

Layout (verified against classical references - Horaratna/Rajavijaya as
preserved in Phaladeepika XXVI, and the Narapatijayacharya tradition):

* 28 nakshatras on the border (7 per side), starting with Krittika on
  the East side and running clockwise.  Abhijit sits between U.Ashadha
  and Shravana.
* 16 vowels (svaras) on the four corners and the two diagonals,
  dealt clockwise from the NE corner.
* 20 name consonants (aksharas) on the inner ring - the avakahada
  scheme, read clockwise from Aa on the SE area of the ring.
* 12 rashis, three per side, Taurus starting East, ending with Aries.
* 5 tithi groups in the centre with the weekdays paired to them.
"""



# Cell types
VOWEL = "vowel"
CONSONANT = "consonant"
NAKSHATRA = "nakshatra"
RASHI = "rashi"
TITHI = "tithi"
CENTER = "center"

# Rows are top (North) to bottom (South), columns left (West) to right
# (East).  North is at the top.
_RAW = [
    ["V:ई", "N:Dhanishta", "N:Shatabhisha", "N:P.Bhadrapada", "N:U.Bhadrapada",
     "N:Revati", "N:Ashwini", "N:Bharani", "V:अ"],
    ["N:Shravana", "V:ॠ", "C:ग", "C:स", "C:द", "C:च", "C:ल", "V:उ", "N:Krittika"],
    ["N:Abhijit", "C:ख", "V:ऐ", "R:Aquarius", "R:Pisces", "R:Aries", "V:ऌ",
     "C:अ", "N:Rohini"],
    ["N:U.Ashadha", "C:ज", "R:Capricorn", "V:अः", "T:Rikta", "V:ओ", "R:Taurus",
     "C:व", "N:Mrigashira"],
    ["N:P.Ashadha", "C:भ", "R:Sagittarius", "T:Jaya", "T:Purna", "T:Nanda",
     "R:Gemini", "C:क", "N:Ardra"],
    ["N:Mula", "C:य", "R:Scorpio", "V:अं", "T:Bhadra", "V:औ", "R:Cancer",
     "C:ह", "N:Punarvasu"],
    ["N:Jyeshtha", "C:न", "V:ए", "R:Libra", "R:Virgo", "R:Leo", "V:ॡ", "C:ड",
     "N:Pushya"],
    ["N:Anuradha", "V:ऋ", "C:त", "C:र", "C:प", "C:ट", "C:म", "V:ऊ", "N:Ashlesha"],
    ["V:इ", "N:Vishakha", "N:Swati", "N:Chitra", "N:Hasta", "N:U.Phalguni",
     "N:P.Phalguni", "N:Magha", "V:आ"],
]

TITHI_WEEKDAYS = {
    "Nanda": ["Sunday", "Tuesday"],
    "Bhadra": ["Monday", "Wednesday"],
    "Jaya": ["Thursday"],
    "Rikta": ["Friday"],
    "Purna": ["Saturday"],
}


_KIND_MAP = {
    "V": VOWEL,
    "C": CONSONANT,
    "N": NAKSHATRA,
    "R": RASHI,
    "T": TITHI,
}


def _parse(cell):
    kind, value = cell.split(":", 1)
    d = {"type": _KIND_MAP.get(kind, kind), "label": value}
    return d


def build_grid():
    """Return the 9x9 grid as a list of rows of cell dicts."""
    grid = []
    for r, row in enumerate(_RAW, start=1):
        cells = []
        for c, cell in enumerate(row, start=1):
            d = _parse(cell)
            d["row"] = r
            d["col"] = c
            d["nakshatra"] = d["label"] if d["type"] == NAKSHATRA else None
            d["rashi"] = d["label"] if d["type"] == RASHI else None
            d["weekdays"] = (
                TITHI_WEEKDAYS.get(d["label"]) if d["type"] == TITHI else None
            )
            cells.append(d)
        grid.append(cells)
    return grid


GRID = build_grid()

NAKSHATRA_CELL = {}
RASHI_CELL = {}
for row in GRID:
    for cell in row:
        if cell["type"] == NAKSHATRA:
            NAKSHATRA_CELL[cell["label"]] = (cell["row"], cell["col"])
        elif cell["type"] == RASHI:
            RASHI_CELL[cell["label"]] = (cell["row"], cell["col"])


def cell_at(row, col):
    if 1 <= row <= 9 and 1 <= col <= 9:
        return GRID[row - 1][col - 1]
    return None


def _diag(cell, dr, dc):
    """Cells along a diagonal ray, including the exit cell, excluding origin."""
    out = []
    r, c = cell["row"], cell["col"]
    while True:
        r += dr
        c += dc
        hit = cell_at(r, c)
        if hit is None:
            break
        out.append(hit)
    return out


def front_line(cell):
    """Straight-across line: the nakshatra directly opposite."""
    r, c = cell["row"], cell["col"]
    if r in (1, 9):
        return cell_at(10 - r, c)
    return cell_at(r, 10 - c)


def diagonals(cell):
    """Return (left_diag, right_diag) cell lists.

    left  = the diagonal in the zodiacal direction of the planet's
            motion along the border (the 'fore' ray)
    right = the diagonal against the direction of motion (the 'hind' ray)

    The zodiacal direction follows the clockwise ring: on the East side
    (right) planets move downward, on the South (bottom) side leftward,
    on the West (left) side upward, on the North (top) side rightward.
    """
    r, c = cell["row"], cell["col"]
    if c == 9:          # East side, moving down
        left, right = _diag(cell, +1, -1), _diag(cell, -1, -1)
    elif r == 9:        # South side, moving left
        left, right = _diag(cell, -1, -1), _diag(cell, -1, +1)
    elif c == 1:        # West side, moving up
        left, right = _diag(cell, -1, +1), _diag(cell, +1, +1)
    else:               # North side, moving right
        left, right = _diag(cell, +1, +1), _diag(cell, +1, -1)
    return left, right


def vedha_cells(cell, planet, school="classical"):
    """Return the list of (cell, ray) hit by a planet's active vedha.

    school:
      classical - one operative ray per graha by motion:
                  swift -> left, retrograde -> right, mean -> front;
                  Sun & Moon always left, Rahu & Ketu always right.
      allthree  - front + both diagonals (Narasimha Rao method).
    """
    speed = planet.get("speed", 0.0)
    name = planet.get("name")
    rays = []

    if school == "allthree":
        rays.append(("front", [front_line(cell)]))
        left, right = diagonals(cell)
        rays.append(("left", left))
        rays.append(("right", right))
        return [(c, ray) for ray, cells in rays for c in cells if c]

    if name in ("Sun", "Moon"):
        left, _ = diagonals(cell)
        ray = "left"
        cells = left
    elif name in ("Rahu", "Ketu") or speed < 0:
        left, right = diagonals(cell)
        ray = "right"
        cells = right
    elif speed > 1.1:
        left, _ = diagonals(cell)
        ray = "left"
        cells = left
    else:
        ray = "front"
        cells = [front_line(cell)]
    return [(c, ray) for c in cells if c]
