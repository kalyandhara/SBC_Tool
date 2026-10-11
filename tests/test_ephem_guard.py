"""B-68: the sidereal mode is per thread, so concurrent Lahiri and KP work can't mix."""

import threading

import sbc  # noqa: F401  (installs the guard)
import swisseph as swe

JD = 2461325.0  # 2026-10-11
FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL


def moon(mode):
    swe.set_sid_mode(mode)
    return swe.calc_ut(JD, swe.MOON, FLAGS)[0][0]


def test_modes_differ_and_are_stable():
    lahiri, kp = moon(swe.SIDM_LAHIRI), moon(swe.SIDM_KRISHNAMURTI)
    assert 0.05 < abs(lahiri - kp) < 0.2  # ~6 arc-minutes
    assert moon(swe.SIDM_LAHIRI) == lahiri


def test_threads_keep_their_own_mode():
    expected = {swe.SIDM_LAHIRI: moon(swe.SIDM_LAHIRI), swe.SIDM_KRISHNAMURTI: moon(swe.SIDM_KRISHNAMURTI)}
    wrong = []
    start = threading.Barrier(8)

    def worker(mode):
        swe.set_sid_mode(mode)
        start.wait()
        for _ in range(400):
            # another thread switches the global mode in between; this thread's result must not move
            if swe.calc_ut(JD, swe.MOON, FLAGS)[0][0] != expected[mode]:
                wrong.append(mode)
                return

    threads = [threading.Thread(target=worker, args=(m,))
               for m in [swe.SIDM_LAHIRI, swe.SIDM_KRISHNAMURTI] * 4]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert wrong == []
