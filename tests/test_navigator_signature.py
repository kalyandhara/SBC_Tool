"""Phase 4 natal signature: hand-set weights, exact values on hand-built cases."""
import datetime as dt

import numpy as np
import pytest

from sbc.navigator import signature as G
from sbc.navigator import terms
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import build_sky
from sbc.yogas import vimshottari

NATAL = {"Sun": 10.0, "Moon": 100.0, "Mars": 200.0, "Jupiter": 275.0, "Lagna": 330.0}


@pytest.mark.parametrize("a,b,expected", [
    ([1, 0], [1, 0], 1.0), ([1, 0], [0, 1], 0.0), ([1, .5], [.5, 1], .5), ([0, 0], [0, 0], 1.0)])
def test_weighted_jaccard(a, b, expected):
    assert G.weighted_jaccard(np.array(a, float), np.array([b], float))[0] == pytest.approx(expected)


def test_weighted_jaccard_pool_rows_independent():
    out = G.weighted_jaccard(np.array([1., .5]), np.array([[1., .5], [.5, 1.], [0., 0.]]))
    assert out.tolist() == pytest.approx([1.0, 0.5, 0.0])


def test_weights_pinned():
    assert (G.ANALOG_VERSION, G.W_CONTACTS, G.W_DASHA, G.W_ANTAR, G.W_PRAT, G.W_NATAL, G.W_SKY) == \
        ("nav-analog-1", .8, .2, .6, .4, .5, .5)


def test_dasha_component_values():
    antar = ["Venus", "Venus", "Mars", "Mars"]; prat = ["Sun", "Moon", "Sun", "Moon"]
    nat = G.natal_similarity(0, np.zeros((4, 1)), antar, prat, np.arange(4))
    # contacts both empty give 1, so natal = .8 + .2 * dasha
    assert nat.tolist() == pytest.approx([.8 + .2, .8 + .2 * .6, .8 + .2 * .4, .8])


def test_natal_is_contacts_plus_dasha_only():
    contacts = np.array([[1., .5, 0.], [.5, 1., 0.], [0., 0., 1.]])
    antar = ["A", "A", "B"]; prat = ["x", "y", "x"]
    nat = G.natal_similarity(0, contacts, antar, prat, np.array([0, 1, 2]))
    jac = [1.0, 1.0 / 2.0, 0.0]       # sums of minimums over maximums, by hand: (.5+.5)/(1+1)
    dash = [1.0, .6, .4]
    assert nat.tolist() == pytest.approx([.8 * j + .2 * d for j, d in zip(jac, dash)])


def test_uncovered_dates_never_match_on_dasha():
    nat = G.natal_similarity(0, np.zeros((2, 1)), ["", ""], ["", ""], np.arange(2))
    assert nat.tolist() == pytest.approx([.8, .8])


def test_blend_exact():
    assert G.blend(np.array([1., 0.]), np.array([0., .5])).tolist() == pytest.approx([.5, .25])


@pytest.fixture(scope="module")
def sky():
    start = dt.date(2024, 3, 1)
    return build_sky([(start + dt.timedelta(days=i)).isoformat() for i in range(40)])


def _sep(a, b):
    return abs((a - b + 180) % 360 - 180)


def test_contact_matrix_matches_direct_computation(sky):
    keys, m = G.contact_matrix(sky, NATAL)
    assert m.shape == (40, len(W.TRANSIT_BODIES) * len(NATAL) * len(W.ASPECTS))
    assert len(set(keys)) == len(keys)
    nonzero = 0
    for k, (planet, point, code) in enumerate(keys):
        for d in range(40):
            f = max(0.0, 1 - abs(_sep(sky.lon[planet][d], NATAL[point]) - W.ASPECTS[code]) / W.ORB)
            assert m[d, k] == pytest.approx(f, abs=1e-12)
            nonzero += f > 0
    assert nonzero > 0  # the window actually exercises contacts


def test_contact_matrix_active_set_equals_phase1_transit_contacts(sky):
    """Same geometry as Phase 1. Phase 1 omits contacts whose table weight is exactly 0
    (they cannot move the score); the signature keeps them, so the only difference
    allowed is that zero-weight set."""
    keys, m = G.contact_matrix(sky, NATAL)
    term = terms.transit_term(sky, NATAL)
    seen = dropped = 0
    for d in range(40):
        phase1 = sorted(f["label"] for f in term.factors(d))
        mine, zero = [], []
        for (p, pt, c), w in zip(keys, m[d]):
            if w > 0:
                label = f"{p} {terms.ASPECT_NAMES[c]} natal {pt}"
                (zero if W.ASPECT_WEIGHT(p, pt, c) == 0 else mine).append(label)
        assert sorted(mine) == phase1
        seen += len(mine); dropped += len(zero)
    assert seen > 0 and dropped > 0   # window exercises both kinds


def test_dasha_lords_match_vimshottari_at_each_day(sky):
    moon, birth = 123.4, "1985-07-09"
    antar, prat = G.dasha_lords(moon, birth, sky.days)
    assert len(antar) == len(prat) == 40
    for d in (0, 13, 39):
        at = vimshottari(moon, birth, sky.days[d])["at"]
        assert (antar[d], prat[d]) == (at["antar"], at["pratyantar"])


def test_dasha_lords_change_within_window_boundary():
    # 1 Jan 2024 .. 31 Mar 2025 for a long window with several Pratyantar changes
    start = dt.date(2024, 1, 1)
    days = [(start + dt.timedelta(days=i)).isoformat() for i in range(450)]
    antar, prat = G.dasha_lords(250.0, "1990-01-01", days)
    assert len(set(prat)) > 1
    for d in (0, 120, 300, 449):
        at = vimshottari(250.0, "1990-01-01", days[d])["at"]
        assert (antar[d], prat[d]) == (at["antar"], at["pratyantar"])


def test_dasha_lords_before_birth_are_blank():
    antar, prat = G.dasha_lords(100.0, "2000-01-01", ["1990-01-01", "2010-01-01"])
    assert (antar[0], prat[0]) == ("", "") and antar[1] and prat[1]
