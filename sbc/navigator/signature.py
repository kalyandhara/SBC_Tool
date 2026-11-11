"""Natal signature similarity for Phase 4 analogs. Hand-set, never fitted.

natal = 0.8 * weighted-Jaccard of active transit contacts + 0.2 * dasha match
(Antardasha 0.6, Pratyantar 0.4; no Mahadasha, no separate natal Moon term).
Blended = 0.5 * natal + 0.5 * sky. Changing any value means a new ANALOG_VERSION."""
from __future__ import annotations

import numpy as np

from sbc.navigator import weights as W
from sbc.navigator.terms import _flatten_periods
from sbc.yogas import vimshottari

ANALOG_VERSION = "nav-analog-1"
W_CONTACTS, W_DASHA = 0.8, 0.2
W_ANTAR, W_PRAT = 0.6, 0.4
W_NATAL, W_SKY = 0.5, 0.5


def contact_matrix(sky, natal):
    """(keys, weights): weights[d, k] is the Phase 1 orb factor of contact k on day d."""
    keys, cols = [], []
    for planet in W.TRANSIT_BODIES:
        for point, nlon in natal.items():
            sep = np.abs((sky.lon[planet] - nlon + 180) % 360 - 180)
            for code, angle in W.ASPECTS.items():
                keys.append((planet, point, code))
                cols.append(np.clip(1 - np.abs(sep - angle) / W.ORB, 0, 1))
    return keys, np.column_stack(cols)


def weighted_jaccard(a, pool):
    mn = np.minimum(pool, a).sum(axis=1)
    mx = np.maximum(pool, a).sum(axis=1)
    out = np.ones(len(pool))
    nz = mx > 0
    out[nz] = mn[nz] / mx[nz]
    return out


def dasha_lords(moon_natal_lon, birth_date, days):
    """Antardasha and Pratyantar lord per day; "" where the date is outside the timeline."""
    timeline = vimshottari(moon_natal_lon, birth_date, days[0])
    when = np.array(days, "datetime64[D]").astype("datetime64[us]")
    periods = _flatten_periods(timeline)
    end = np.datetime64(timeline["mahadashas"][-1]["end"], "us")
    covered = (when >= periods["maha"][0][0]) & (when < end)
    out = []
    for level in ("antar", "pratyantar"):
        starts, names = periods[level]
        at = np.clip(np.searchsorted(starts, when, side="right") - 1, 0, len(names) - 1)
        out.append([str(n) if c else "" for n, c in zip(names[at], covered)])
    return out[0], out[1]


def natal_similarity(target_idx, contacts, antar, prat, pool_idx):
    c = weighted_jaccard(contacts[target_idx], contacts[pool_idx])
    a = np.array([bool(antar[target_idx]) and antar[i] == antar[target_idx] for i in pool_idx], float)
    p = np.array([bool(prat[target_idx]) and prat[i] == prat[target_idx] for i in pool_idx], float)
    return W_CONTACTS * c + W_DASHA * (W_ANTAR * a + W_PRAT * p)


def blend(natal, sky):
    return W_NATAL * natal + W_SKY * sky
