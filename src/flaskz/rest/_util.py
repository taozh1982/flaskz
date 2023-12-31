from functools import wraps

from flask import current_app

from ..utils import get_wrap_str, filter_list

__all__ = ['get_current_model_rest_manager_callback',
           'rest_login_required', 'rest_permission_required',
           'get_rest_log_msg',
           'log_operation',
           'gen_route_method']


def get_current_model_rest_manager_callback(callback_name):
    if current_app:
        model_rest_manager = getattr(current_app, 'model_rest_manager', None)
        if model_rest_manager:
            return getattr(model_rest_manager, callback_name, None)


def rest_login_required():
    """
    If you decorate a view with this, it will ensure that the current user is logged in and authenticated before calling the actual view.

    Example:
        @sys_mgmt_bp.route('/auth/account/', methods=['GET', 'POST'])
        @rest_login_required()
        def sys_auth_account_query():
            pass

    :return:
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            check_result = True
            login_check_callback = get_current_model_rest_manager_callback('login_check_callback')
            if login_check_callback:
                check_result = login_check_callback()
            if check_result is not True:
                return check_result
            return func(*args, **kwargs)

        return wrapper

    return decorate


def rest_permission_required(module, action=None):  # @2023-10-10, op_permission--> action
    """
    If you decorate a view with this, it will ensure that the current user.
    has the module permission and action permission before calling the actual view.

    Example:
        @sys_mgmt_bp.route('/role/', methods=['GET'])
        @rest_permission_required('role')
        def sys_role_query():
            pass

        @sys_mgmt_bp.route('/role/', methods=['POST'])
        @rest_permission_required('role', 'add')
        def sys_role_add():
            pass

    :param module: module permission to be checked
    :param action: action permission to be checked
    :return:
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            check_result = True
            permission_check_callback = get_current_model_rest_manager_callback('permission_check_callback')
            if permission_check_callback:
                check_result = permission_check_callback(module, action)
            if check_result is not True:
                return check_result
            return func(*args, **kwargs)

        return wrapper

    return decorate


def get_rest_log_msg(api_info, req_data, success, res_data):
    """
    Return the log message text.

    :param api_info:
    :param req_data:
    :param success:
    :param res_data:
    :return:
    """
    return get_wrap_str(
        '--' + api_info,
        '--Request data:', req_data,
        '--Response result:' + str(success),
        '--Response data:', res_data)


def log_operation(*args, **kwargs):
    """
    Log operation/action.

    Example:
        log_operation('users', 'login', success, request_json.get('username'), res_data)

    :param args:
    :param kwargs:
    :return:
    """
    logging_callback = get_current_model_rest_manager_callback('logging_callback')
    if logging_callback:
        logging_callback(*args, **kwargs)


def gen_route_method(method, url_prefix, view_func_name=None):
    """
    Generate endpoint unique function name.

    :param method:
    :param url_prefix:
    :param view_func_name:
    :return:
    """

    def decorator(f):
        def wrap(*args, **kwargs):
            return f(*args, **kwargs)

        if view_func_name is None:
            methods = url_prefix.split('/')
            methods.append(method)
            methods.insert(0, 'model_route')
            wrap.__name__ = '_'.join(filter_list(methods, lambda item: item != '')).replace('-', '_')
        else:
            wrap.__name__ = view_func_name
        return wrap

    return decorator
