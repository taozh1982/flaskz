import os

from flask import current_app

__all__ = ['get_app_path', 'get_app_config']


def get_app_path(*path):
    """
    Get the application path.
    app.get_app_path("_log", "sys.log")
    :param path:    -The relative path
    :return:        -The path relative to the application root directory
    """
    return os.path.join(os.getcwd(), *path)


def get_app_config(key):
    """
    Set the specified config value of the current app
    :param key:
    :return:
    """
    return current_app.config.get(key)
