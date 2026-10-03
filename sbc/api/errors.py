"""JSON error responses that don't leak exception text to the client (B-25)."""

from flask import current_app, jsonify, request


def internal_error(message: str = "internal error"):
    """Log the active exception with its traceback; answer a generic JSON 500.

    Call from inside an `except` block. The client gets `message`, never the
    exception text, which can carry file paths, SQL or library internals.
    """
    current_app.logger.exception("Error handling %s %s", request.method, request.path)
    return jsonify({"error": message}), 500
