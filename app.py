"""Sarvatobhadra Chakra market prediction - Flask app.

The app is built by sbc.app_factory.create_app(); routes live in blueprints
under sbc/api/ (B-16). This module keeps `app` for gunicorn (`app:app`),
run_app.py and the tests.
"""

from sbc.app_factory import create_app

# The prediction engine lives in sbc/engine.py; re-exported here for callers
# that use app.build_response, app.ANCHORS, app._utc_from_local, ...
from sbc.engine import (  # noqa: F401
    ANCHORS,
    WEEKDAYS,
    _anchor_nakshatra,
    _julday,
    _tithi_info,
    _utc_from_local,
    build_response,
)

app = create_app()


if __name__ == "__main__":
    # Bare server on the same port as run_app.py, gunicorn and Docker. Use
    # run_app.py for the cache warm-up, forecast ledger loop and CLI flags.
    # Nothing under sbc/ imports `app`, so running this file as __main__ no
    # longer loads it a second time (which used to create two Flask apps).
    app.run(host="127.0.0.1", port=8000, debug=False)
