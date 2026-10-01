"""Single boot entrypoint for SBC app."""
from sbc.db import _bootstrap


def boot(app, build_response=None):
    """Cheap, import-time setup only.

    The prediction-series warm-up lives in run_app.py, which calls the real
    /api/prediction_series endpoint in a background thread. Warming here used
    to block import for minutes and wrote a trimmed payload (no drivers,
    risk bands or windows) into the same cache the chart reads.
    """
    _bootstrap()
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}
