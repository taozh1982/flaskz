import os

from flask import current_app

__all__ = ['init_app_config', 'get_app_config', 'get_app_config_items', 'get_app_path']

app_config = None


def init_app_config(app):
    """
    Initialize application(flask/celery/script/...) configuration.
    Once initialized, the application configuration can be get through get_app_config function anywhere.

    .. versionadded:: 1.5

    Example:
        init_app_config(app)    # Flask
        init_app_config(DevelopmentConfig)  # Class
        init_app_config({...})  # dict


    :param app:Flask/Config/dict
    :return:
    """
    config = get_app_config_items(app)
    if type(config) is dict:
        global app_config
        app_config = config


def get_app_config(key=None, default=None):
    """
    Get the specified config value of the application(flask/celery/script/...).
    If the config is initialized by init_app_config, return the initialized config, otherwise return the config of the current flask application.
    If key is None, return all config values(dict), otherwise return the specified config value

    .. versionupdated::
        1.5 -
        1.6.4 - add default

    Example:
        get_app_config()                        # all Config
        get_app_config('FLASKZ_LOGGER_LEVEL')   # specified config value

    :param key:
    :param default:
    :return:
    """
    config = None
    if app_config:
        config = app_config
    elif current_app:
        config = dict(current_app.config.items())

    if type(config) is not dict:
        config = {}

    if key is None:
        return config
    return config.get(key, default)


def get_app_config_items(app):
    """
    Return config items(dict)

    :param app:
    :return:
    """
    items = None
    if hasattr(app, 'config'):  # Flask
        _app_config = getattr(app, 'config')
        if _app_config:
            items = dict(_app_config.items())
    elif isinstance(app, type):  # Class
        items = cls_to_dict(app)
    else:
        items = app  # dict
    if type(items) is dict:
        return items
    return None


def get_app_path(*path):
    """
    Get the application path.

    Example:
        app.get_app_path("_log", "sys.log")

    :param path:    -The relative path
    :return:        -The path relative to the application root directory
    """
    return os.path.join(os.getcwd(), *path)


from ._cls import cls_to_dict
