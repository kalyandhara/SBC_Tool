"""KP Intraday blueprint."""

from flask import Blueprint, jsonify, request, Response, send_file
import datetime
from io import BytesIO
from pathlib import Path

kp_bp = Blueprint('kp', __name__, url_prefix='')

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@kp_bp.route('/api/kp_intraday_report')
def kp_intraday_report():
    from sbc.kp_intraday import (
        generate_kp_intraday_report, report_to_dict, KPReportGenerator
    )
    from sbc.kp_config import get_config, get_instrument_config
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    instrument = request.args.get("instrument", "NIFTY")
    format_type = request.args.get("format", "json")
    try:
        trading_day = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    if instrument not in ("NIFTY", "BANK NIFTY", "FINNIFTY"):
        return jsonify({"error": "invalid instrument"}), 400
    kp_data_dir = Path(__file__).resolve().parents[3] / "data" / "kp"
    kp_data_dir.mkdir(parents=True, exist_ok=True)
    month_file = kp_data_dir / f"KP_Data_{trading_day.strftime('%b%Y')}.csv"
    if not month_file.exists():
        return jsonify({
            "error": (
                f"KP data unavailable for {trading_day.strftime('%B %Y')}. "
                "Use 'Generate Sample Data' to create it explicitly."
            )
        }), 404
    config = get_config()
    instrument_cfg = get_instrument_config(instrument, config)
    report = generate_kp_intraday_report(month_file, trading_day, instrument, instrument_cfg)
    if format_type == "json":
        return jsonify(report_to_dict(report))
    if format_type == "html":
        html = KPReportGenerator(instrument_cfg).generate_html(report)
        return Response(html, mimetype="text/html")
    if format_type == "docx":
        from sbc.kp_docx import render_docx
        buf = render_docx(report)
        filename = f"KP_Intraday_Prediction_Report_{trading_day.isoformat()}.docx"
        return send_file(BytesIO(buf), as_attachment=True, download_name=filename, mimetype=_DOCX_MIME)
    return jsonify({"error": "unsupported format"}), 400

@kp_bp.route('/api/kp_intraday_config')
def kp_intraday_config():
    from sbc.kp_config import get_config
    config = get_config()
    return jsonify(config.to_dict())
