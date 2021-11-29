import datetime
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from flask import Flask
from werkzeug.local import LocalProxy

_flaskz_logger: logging.Logger
flaskz_logger = LocalProxy(lambda: _get_app_logger())


def init_log(app):
    """
    Initialize system log configuration
    :param app:
    :return:
    """
    if isinstance(app, Flask):
        app_config = app.config
    else:
        app_config = app
    level = logging.getLevelName(app_config.get('FLASKZ_LOGGER_LEVEL'))
    formatter = logging.Formatter(app_config.get('FLASKZ_LOGGER_FORMAT'))
    global _flaskz_logger
    _flaskz_logger = logging.getLogger('flaskz_logger')
    _flaskz_logger.setLevel(level)
    filename = app_config.get('FLASKZ_LOGGER_FILENAME')

    if filename is not None:
        filepath = os.path.join(app_config.get('FLASKZ_LOGGER_FILEPATH') or os.path.join(os.getcwd(), './syslog'), filename)
        log_handler = TimedRotatingFileHandler(
            encoding='utf-8',
            filename=filepath,
            when=app_config.get('FLASKZ_LOGGER_WHEN'),
            interval=1,
            backupCount=int(app_config.get('FLASKZ_LOGGER_BACKUP_COUNT')))
    else:
        log_handler = logging.StreamHandler()

    log_handler.setLevel(level)
    log_handler.setFormatter(formatter)
    _flaskz_logger.addHandler(log_handler)
    _flaskz_logger.disabled = app_config.get('FLASKZ_LOGGER_DISABLED') is True

    wz_logger = logging.getLogger('werkzeug')
    wz_logger.disabled = app_config.get('FLASKZ_WZ_LOGGER_DISABLED') is True


def _get_app_logger():
    return _flaskz_logger or logging.getLogger('flaskz_logger')


def get_log_data(data):
    return json.dumps(data, default=_log_data_converter)


def _log_data_converter(value):
    if isinstance(value, datetime.datetime):
        return value.__str__()