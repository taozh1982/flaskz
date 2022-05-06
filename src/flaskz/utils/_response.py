from flask import current_app

from ._app import get_app_config

__all__ = ['create_response', 'get_status_msg', 'ResponseManager']


def create_response(success, data, data_wrapped=False):
    """
    Create the response json result.
    :param success:
    :param data:
    :param data_wrapped:
    :return:
    """
    if success is True:
        return _create_success_response(data, data_wrapped)
    else:
        return _create_fail_response(data)


def _create_success_response(data, data_wrapped=False):
    """
    :param data:
    :param data_wrapped:
    :return:
    """
    status = get_app_config('FLASKZ_RES_SUCCESS_STATUS') or 'success'
    if data_wrapped is True:
        _data = {
            'status': status,
        }
        _data.update(data)
        return _data
    else:
        return {
            'status': status,
            'data': data
        }


def _create_fail_response(status_code, msg=None):
    """
    :param msg:
    :param status_code:
    :return:
    """
    status = get_app_config('FLASKZ_RES_FAIL_STATUS') or 'fail'
    msg = msg or get_status_msg(status_code)

    if type(status_code) == tuple:
        status_code = status_code[0]

    return {
        'status': status,
        'status_code': status_code,
        'message': str(msg),
    }


def get_status_msg(status_code):
    """
    Get the specified message by status_code.
    Can be used to return internationalized text, Local can be fixed, or get the local from request
    :param status_code:
    :return:
    """
    response_callback = get_current_response_manager('get_response_callback')
    if response_callback:
        return response_callback(status_code)

    if type(status_code) == tuple:
        len_ = len(status_code)
        if len_ > 1:
            return status_code[1] or status_code[0]
        elif len_ > 0:
            return status_code[0]
    return status_code


def get_current_response_manager(callback_name):
    response_manager = getattr(current_app, 'response_manager', None)
    if response_manager:
        return getattr(response_manager, callback_name)


class ResponseManager:
    """
    Used to generate response.
    """

    def __init__(self):
        self._get_response = None

    def init_app(self, app):
        app.response_manager = self

    def get_response(self, get_response):
        self._get_response = get_response

    @property
    def get_response_callback(self):
        return self._get_response
