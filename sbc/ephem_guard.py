"""Make Swiss Ephemeris' sidereal mode per-thread (B-68).

pyswisseph keeps the ayanamsa set by swe.set_sid_mode() as one process-wide setting.
The tool uses two (Lahiri almost everywhere, Krishnamurti in sbc.kp_ephemeris), and the
server runs requests and background jobs (series warm-up, forecast ledger) on several
threads. Without this guard, one thread can switch the mode between another thread's
set_sid_mode() and its calc_ut(), silently giving a Lahiri result in KP (~6' off, about
10 minutes of Moon timing).

install() wraps the module in place: set_sid_mode() records the mode for the calling
thread, and every function that reads the mode applies that thread's mode under one lock
before it runs. Modules keep writing `swe.set_sid_mode(...)` / `swe.calc_ut(...)` as before.
A thread that never set a mode uses the last mode set by any thread (the old behaviour).
"""

from __future__ import annotations

import threading

import swisseph as swe

# Functions whose result depends on the sidereal mode.
_MODE_READERS = ("calc_ut", "calc", "houses_ex", "houses_ex2", "get_ayanamsa_ut",
                 "get_ayanamsa_ex_ut", "get_ayanamsa", "get_ayanamsa_ex", "fixstar_ut",
                 "fixstar2_ut", "nod_aps_ut")

_lock = threading.RLock()
_local = threading.local()
_state = {"installed": False, "last": None}


def install() -> None:
    if _state["installed"]:
        return
    original_set = swe.set_sid_mode

    def set_sid_mode(mode, t0=0.0, ayan_t0=0.0):
        args = (mode, t0, ayan_t0)
        _local.args = args
        with _lock:
            _state["last"] = args
            original_set(*args)

    def guard(fn):
        def wrapped(*a, **k):
            args = getattr(_local, "args", None) or _state["last"]
            with _lock:
                if args is not None:
                    original_set(*args)
                return fn(*a, **k)
        wrapped.__name__ = getattr(fn, "__name__", "wrapped")
        wrapped.__doc__ = getattr(fn, "__doc__", None)
        wrapped.__wrapped__ = fn
        return wrapped

    for name in _MODE_READERS:
        fn = getattr(swe, name, None)
        if fn is not None:
            setattr(swe, name, guard(fn))
    swe.set_sid_mode = set_sid_mode
    _state["installed"] = True
