from inspect import isawaitable

from .context import begin_context, end_context, get_context_option, get_context_value, has_context, set_context_option, set_context_value
from .. import consts
from .._compat.fastapi import Request

_REQUEST_CONTEXT_INIT_KEY = '_flaskz_request_context_initialized'
_DB_SESSION_CACHE_ENABLED_OPTION = '_cache_db_session_$_'


class FlaskzContextMiddleware:
    """Manage the flaskz execution context for ASGI HTTP requests."""

    def __init__(self, app, value=None, on_context_begin=None, on_context_end=None, **kwargs):
        self.app = app
        self.value = value
        self.on_context_begin = on_context_begin
        self.on_context_end = on_context_end
        self.kwargs = kwargs

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        context_key = begin_context(self.value, context_key=consts.FLASKZ_APP_REQUEST_CONTEXT_KEY)  # specified context_key for get_request_json
        set_context_db_session_cache_enabled(True, context_key=context_key)  # enable db_session cache

        exception = None
        try:
            # Cache JSON request data.
            _receive = receive
            if self.kwargs.get('cache_request_json') is not False:
                request = Request(scope, receive)
                content_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
                if content_type == 'application/json' or content_type.endswith('+json'):
                    body = await request.body()
                    set_context_value('_flaskz_app_request_json_$_', body, context_key=context_key)

                    # Replay the body for downstream ASGI applications.
                    replayed = False

                    async def replay_receive():
                        nonlocal replayed
                        if not replayed:
                            replayed = True
                            return {
                                'type': 'http.request',
                                'body': body,
                                'more_body': False,
                            }
                        return await receive()

                    _receive = replay_receive

            await _call_context_callback(self.on_context_begin, context_key)
            await self.app(scope, _receive, send)
        except BaseException as exc:
            exception = exc
            raise
        finally:
            try:
                await _call_context_callback(self.on_context_end, context_key, exception)
            finally:
                end_context(context_key=context_key)


def init_flask_request_context(flask_app, value=None, on_context_begin=None, on_context_end=None, **kwargs):
    """
    Register execution-context lifecycle hooks for a Flask application.

    A new execution context is created before each request and removed
    during request teardown.

    ``on_context_begin`` is called after context creation as
    ``on_context_begin(context_key)``.

    ``on_context_end`` is called before context removal as
    ``on_context_end(context_key, exception)``. ``exception`` is the exception
    that caused request teardown, or ``None`` if request processing
    completed normally.

    The context is removed in a ``finally`` block, so it is still removed
    if ``on_context_end`` raises an exception.

    :param flask_app: Flask application instance.
    :param value: Optional initial context dictionary, shallow-copied for
        each request.
    :param on_context_begin: Optional callback invoked after context
        creation.
    :param on_context_end: Optional callback invoked before context
        removal.
    """
    if flask_app.extensions.get(_REQUEST_CONTEXT_INIT_KEY):
        return flask_app

    @flask_app.before_request
    def flaskz_begin_context():
        context_key = begin_context(value, context_key=consts.FLASKZ_APP_REQUEST_CONTEXT_KEY)  # specified context_key for get_request_json
        set_context_db_session_cache_enabled(True, context_key=context_key)  # enable db_session cache
        if callable(on_context_begin):
            on_context_begin(context_key)

    @flask_app.teardown_request
    def flaskz_end_context(exception=None):
        context_key = consts.FLASKZ_APP_REQUEST_CONTEXT_KEY
        if not has_context(context_key=context_key):
            return

        try:
            if callable(on_context_end):
                on_context_end(context_key, exception)
        finally:
            end_context(context_key=context_key)

    flask_app.extensions[_REQUEST_CONTEXT_INIT_KEY] = True
    return flask_app


def init_fastapi_request_context(fastapi_app, value=None, on_context_begin=None, on_context_end=None, **kwargs):
    """
    Initialize request-scoped flaskz context management for FastAPI.

    Args:
        fastapi_app: FastAPI application instance.
        value: Initial context value.
        on_context_begin: Callback invoked after context creation.
        on_context_end: Callback invoked before context cleanup.

    Returns:
        The original FastAPI application instance.
    """
    if getattr(fastapi_app.state, _REQUEST_CONTEXT_INIT_KEY, False):
        return fastapi_app

    fastapi_app.add_middleware(FlaskzContextMiddleware, value=value, on_context_begin=on_context_begin, on_context_end=on_context_end, **kwargs)
    setattr(fastapi_app.state, _REQUEST_CONTEXT_INIT_KEY, True)

    return fastapi_app


def get_request_context_value(key, default=None):
    """Get a value from the request context, or return the default."""
    return get_context_value(key, default=default, context_key=consts.FLASKZ_APP_REQUEST_CONTEXT_KEY)


def set_request_context_value(key, value):
    """Set a value in the request context."""
    return set_context_value(key, value, context_key=consts.FLASKZ_APP_REQUEST_CONTEXT_KEY)


def set_context_db_session_cache_enabled(enabled=True, *, context_key=None):
    """
    Enable or disable database session caching in an execution context.

    :param enabled: True to enable caching, False to disable it.
    :param context_key: Context key. None selects the current context.
    :return: True if set, False if the context does not exist.
    """
    return set_context_option(_DB_SESSION_CACHE_ENABLED_OPTION, enabled, context_key=context_key)


def get_context_db_session_cache_enabled(*, context_key=None):
    """
    Get the database session caching option.

    :param context_key: Context key. None selects the current context.
    :return: True or False if configured, otherwise None.
             None is also returned when the context does not exist.
    """
    return get_context_option(_DB_SESSION_CACHE_ENABLED_OPTION, context_key=context_key)


# ------------------------------------------- internal-------------------------------------------
async def _call_context_callback(callback, *args):
    """
    Execute a synchronous or asynchronous context callback.

    If the callback returns an awaitable object, it is awaited.

    :param callback: Synchronous or asynchronous callable.
    :param args: Positional arguments passed to the callback.
    :return: Callback result, or None if callback is not callable.
    """
    if not callable(callback):
        return None
    result = callback(*args)
    if isawaitable(result):
        return await result
    return result
