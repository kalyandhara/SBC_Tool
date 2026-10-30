"""Infographic blueprint: one PNG card per research tab (sbc/infographic.py)."""

import datetime

from flask import Blueprint, Response, current_app, jsonify, request

infographic_bp = Blueprint('infographic', __name__, url_prefix='')


@infographic_bp.route('/api/infographic/<page>')
def infographic(page):
    from sbc import infographic as ig

    if page not in ig.PAGES:
        return jsonify({"error": "unknown infographic page"}), 404
    today = datetime.date.today()
    # The tab's own endpoint builds the numbers, so the card matches the screen.
    # Query args from the button override the defaults; the endpoint validates them.
    args = {**ig.defaults(page, today), **request.args.to_dict()}
    client = current_app.test_client()
    upstream = client.get(ig.PAGES[page].endpoint, query_string=args)
    body = upstream.get_json(silent=True) or {}
    if upstream.status_code == 400 and body.get("next_trading_day"):
        # The picked date is a market holiday; the KP report names the next session.
        args["date"] = body["next_trading_day"]
        upstream = client.get(ig.PAGES[page].endpoint, query_string=args)
    if upstream.status_code != 200:
        return jsonify(upstream.get_json(silent=True) or {"error": "source unavailable"}), upstream.status_code
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")
    png = ig.render(page, upstream.get_json(), stamp)
    name = f"sbc-{page}-{datetime.date.today().isoformat()}.png"
    return Response(png, mimetype="image/png",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})
