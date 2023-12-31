import warnings

from flask import request

__all__ = ['get_remote_addr', 'is_ajax', 'get_request_json', 'get_pss']


def get_remote_addr():
    """
    Get the remote ip address of the current request.

    :return:
    """
    if request:
        return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)


def is_ajax():
    """
    Check if the request is an ajax request.

    :return:
    """
    if request:
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    return False


def get_request_json(*args):
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
