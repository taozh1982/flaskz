try:
    from flask import Flask, current_app, g, request, has_app_context, has_request_context

    FLASK_AVAILABLE = True

except ImportError:
    Flask = None
    current_app = None
    g = None
    request = None
    FLASK_AVAILABLE = False


    def has_app_context():
        return False


    def has_request_context():
        return False


def is_flask_app(app):
    return FLASK_AVAILABLE and Flask is not None and isinstance(app, Flask)
