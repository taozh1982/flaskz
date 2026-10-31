import json
import warnings

from .. import consts
from .._compat.flask import has_request_context as has_flask_request_context, request
from ..app import get_context_value

__all__ = ['get_remote_addr', 'is_ajax', 'get_request_json', 'get_pss']


def get_remote_addr():
    """
    Get the remote ip address of the current request.

    :return:
    """
    if request:
        return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    return None


def is_ajax():
    """
    Check if the request is an ajax request.

    :return:
    """
    if request:
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    return False


def get_request_json(default):
    if has_flask_request_context():
        return get_flaskz_request_json(default)

    context_key = consts.FLASKZ_APP_REQUEST_CONTEXT_KEY
    data = get_context_value('_flaskz_app_request_json_$_', context_key=context_key)
    if data is None:
        return default

    if isinstance(data, (str, bytes)):
        try:
            data = json.loads(data)
        except Exception:
            return default

    return data


def get_flaskz_request_json(*args):
    """
    Get the JSON data(parsed) in request.
    If json does not exist or parsing json error, return {}

    .. versionadded:: 1.3

    :return:
    """
    data = None
    try:
        data = request.get_json(force=True, silent=True)
    except Exception:
        pass
    if data is None:
        if len(args) > 0:
            return args[0]
    return data


def get_pss(*args, **kwargs):
    warnings.warn('flaskz.utils.get_pss() has been replaced by flaskz.models.parse_pss()', category=DeprecationWarning)
    return parse_pss(*args, **kwargs)


from ..models._query_util import parse_pss
