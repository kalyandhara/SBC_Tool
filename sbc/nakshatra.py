"""Nakshatra (lunar mansion) definitions and sensitive-point system.

The Sarvatobhadra Chakra works on the 28-star ring: the 27 classical
nakshatras plus Abhijit, which gets its own cell between Uttara Ashadha
and Shravana.

Abhijit span (sidereal, Lahiri): 276°40' to 280°53'20".
"""

NAKSHATRAS_27 = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "P.Ashadha", "U.Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "P.Bhadrapada", "U.Bhadrapada", "Revati",
]

# Full 28-star ring in zodiacal order. Abhijit is inserted between
# U.Ashadha and Shravana.
RING_28 = list(NAKSHATRAS_27[:21]) + ["Abhijit"] + list(NAKSHATRAS_27[21:])

RING_28_INDEX = {name: i for i, name in enumerate(RING_28)}

NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20'

ABHIJIT_START = 276.0 + 40.0 / 60.0  # 276°40'
ABHIJIT_END = 280.0 + 53.0 / 60.0 + 20.0 / 3600.0  # 280°53'20"


def nakshatra_of(longitude):
    """Return (nakshatra name, pada 1-4) for a sidereal longitude."""
    lon = longitude % 360.0
    if ABHIJIT_START <= lon < ABHIJIT_END:
        return "Abhijit", 1
    idx = int(lon // NAKSHATRA_SPAN)
    if idx >= 27:
        idx = 26
    pada = int((lon % NAKSHATRA_SPAN) // (NAKSHATRA_SPAN / 4.0)) + 1
    return NAKSHATRAS_27[idx], pada


def sign_of(longitude):
    """Return (rashi name, sign index 0-11) for a sidereal longitude."""
    idx = int(longitude % 360.0) // 30
    return RASHIS[idx], idx


RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


SENSITIVE_POINTS = [
    ("Janma", 1, "Anchor point - the market's core vitality and trend direction"),
    ("Karma", 10, "Performance, growth and status of the index"),
    ("Sanghatika", 16, "Associations, institutions and liquidity pools"),
    ("Samudayika", 18, "Broad market fortune and investor sentiment"),
    ("Adhana", 19, "New listings, undertakings and fresh capital"),
    ("Vainashika", 23, "Losses, sell-offs and breakdown risk"),
    ("Jati", 26, "Sector breadth and internal market family"),
    ("Desa", 27, "Domestic economy and country-wide conditions"),
    ("Abhisheka", 28, "Benchmark leadership and index reputation"),
]

# The five points used for the Pancha-Shakha market read.
PS_POINT_NAMES = ["Janma", "Karma", "Sanghatika", "Samudayika", "Adhana"]

POINT_OFFSET = {name: off for name, off, _ in SENSITIVE_POINTS}


def sensitive_stars(birth_nakshatra):
    """Return the 9 sensitive nakshatras counted from a birth nakshatra.

    Counting runs forward over the 28-star ring, Janma being the birth
    star itself. Returns a list of dicts: {name, offset, nakshatra,
    description}.
    """
    if birth_nakshatra not in RING_28_INDEX:
        raise ValueError("Unknown nakshatra: %s" % birth_nakshatra)
    start = RING_28_INDEX[birth_nakshatra]
    result = []
    for point_name, offset, description in SENSITIVE_POINTS:
        star = RING_28[(start + offset - 1) % 28]
        result.append({
            "name": point_name,
            "offset": offset,
            "nakshatra": star,
            "description": description,
        })
    return result


# Tithi groups (Panchang: five groups, each with its weekday rulers).
TITHI_GROUPS = {
    "Nanda": {1, 6, 11, 16, 21, 26},
    "Bhadra": {2, 7, 12, 17, 22, 27},
    "Jaya": {3, 8, 13, 18, 23, 28},
    "Rikta": {4, 9, 14, 19, 24, 29},
    "Purna": {5, 10, 15, 20, 25, 30},
}

GROUP_WEEKDAYS = {
    "Nanda": ["Sunday", "Tuesday"],
    "Bhadra": ["Monday", "Wednesday"],
    "Jaya": ["Thursday"],
    "Rikta": ["Friday"],
    "Purna": ["Saturday"],
}

GROUP_OF_TITHI = {}
for group, tithis in TITHI_GROUPS.items():
    for t in tithis:
        GROUP_OF_TITHI[t] = group


def tithi_of(sun_lon, moon_lon):
    """Lunar tithi 1-30 (Shukla 1-15, Krishna 16-30)."""
    diff = (moon_lon - sun_lon) % 360.0
    return int(diff // 12.0) + 1


def paksha_of(tithi):
    return "Shukla" if tithi <= 15 else "Krishna"


def moon_nature(tithi):
    """Moon is ashubha (malefic) from Krishna Ekadashi through Shukla
    Chaturthi, shubha otherwise (per classical boundary)."""
    if tithi >= 26 or tithi <= 4:
        return "malefic"
    return "benefic"


# 27 nitya yogas: index = floor((sun_lon + moon_lon) % 360 / 13deg20').
NITYA_YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarman", "Dhriti", "Shula", "Ganda", "Vriddhi",
    "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
    "Variyan", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
    "Shukla", "Brahma", "Indra", "Vaidhriti",
]
VYATIPATA_INDEX = 16


def nitya_yoga_of(sun_lon, moon_lon):
    """Return (index 0-26, name) of the nitya yoga at a moment."""
    total = (sun_lon + moon_lon) % 360.0
    index = int(total // NAKSHATRA_SPAN)
    return index, NITYA_YOGA_NAMES[index]


def gandanta_of(longitude):
    """Check if a sidereal longitude falls at a Gandanta junction.

    Gandanta are critical junction points where sign elements change
    (water-fire boundaries): Pisces→Aries, Cancer→Leo, Scorpio→Sagittarius.
    A longitude is 'at gandanta' if within ~1.5° of these junctions.
    """
    lon = longitude % 360.0
    # Junction 1: Pisces (330-360) / Aries (0-30)
    if (358.5 <= lon <= 360.0) or (0.0 <= lon <= 1.5):
        return True
    # Junction 2: Cancer (90-120) / Leo (120-150)
    if (88.5 <= lon <= 90.0) or (120.0 <= lon <= 121.5):
        return True
    # Junction 3: Scorpio (210-240) / Sagittarius (240-270)
    return bool(208.5 <= lon <= 210.0 or 240.0 <= lon <= 241.5)
