import datetime
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Union

from werkzeug.local import LocalProxy

_flaskz_logger: logging.Logger = None  # @2022-04-27: fix _get_app_logger --> NameError: name '_flaskz_logger' is not defined
flaskz_logger: Union[LocalProxy, logging.Logger] = LocalProxy(lambda: _get_app_logger())  # @2023-05-15: add type Union


def init_log(app):
    """
    Initialize system log configuration

    Example:
        init_log(app)

    :param app:
    :return:
    """
    app_config = get_app_config_items(app) or {}
    level = logging.getLevelName(app_config.get('FLASKZ_LOGGER_LEVEL'))
    formatter = logging.Formatter(app_config.get('FLASKZ_LOGGER_FORMAT'))
    global _flaskz_logger
    _flaskz_logger = logging.getLogger('flaskz_logger')
    _flaskz_logger.setLevel(level)

    log_handler = app_config.get('FLASKZ_LOGGER_HANDLER')
    if log_handler is None:
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


def clear_log_handler():
    logger = _get_app_logger()
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def _get_app_logger():
    return _flaskz_logger or logging.getLogger('flaskz_logger')


def get_log_data(data):
    return json.dumps(data, default=_log_data_converter)


def _log_data_converter(value):
    if isinstance(value, datetime.datetime):
        return value.__str__()


from ..utils._app import get_app_config_items
