"""
Navamsa D-9 divisional mapping.

Navamsa divides each rashi into 9 parts of 3°20' each.
Mapping is based on sidereal longitude.
"""
from dataclasses import dataclass

@dataclass
class NavamsaResult:
    navamsa_sign: str
    navamsa_deg: float
    navamsa_index: int
    vargottama_flag: bool

RASHIS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

NAVAMSA_LORDS = [
    "Mars","Sun","Moon","Mars","Mercury","Jupiter",
    "Venus","Saturn","Mercury","Moon","Venus","Sun",
    "Mars","Mercury","Jupiter","Venus","Saturn","Moon",
    "Sun","Venus","Mercury","Saturn","Jupiter","Mars",
    "Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Mercury","Moon","Venus","Sun"
]

def navamsa_of(longitude):
    """Return Navamsa mapping for sidereal longitude."""
    lon = longitude % 360.0
    sign_idx = int(lon // 30)
    sign_deg = lon % 30.0
    navamsa_idx_in_sign = int(sign_deg // (30.0/9))
    navamsa_deg_in_sign = sign_deg % (30.0/9)
    navamsa_index = sign_idx * 9 + navamsa_idx_in_sign
    navamsa_sign = RASHIS[navamsa_idx_in_sign % 12]
    # Vargottama if sign matches original sign
    vargottama = RASHIS[sign_idx] == navamsa_sign
    return NavamsaResult(
        navamsa_sign=navamsa_sign,
        navamsa_deg=navamsa_deg_in_sign,
        navamsa_index=navamsa_index,
        vargottama_flag=vargottama
    )
