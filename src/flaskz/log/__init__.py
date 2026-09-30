import json
import logging
import os
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from logging.handlers import TimedRotatingFileHandler

flaskz_logger = logging.getLogger('flaskz_logger')  # @2026-09-10: change <-- LocalProxy(lambda: _get_app_logger())


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
    flaskz_logger.setLevel(level)

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
    flaskz_logger.addHandler(log_handler)
    flaskz_logger.disabled = app_config.get('FLASKZ_LOGGER_DISABLED') is True

    wz_logger = logging.getLogger('werkzeug')
    wz_logger.disabled = app_config.get('FLASKZ_WZ_LOGGER_DISABLED') is True


def clear_log_handler():
    for handler in list(flaskz_logger.handlers):
        flaskz_logger.removeHandler(handler)


def get_log_data(data):
    return json.dumps(data, default=_log_data_converter, ensure_ascii=False)


def _log_data_converter(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, bytes, bytearray)):
        return str(value)
    if isinstance(value, set):
        return list(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Object of type '{value.__class__.__name__}' is not JSON serializable")


from ..utils._app import get_app_config_items
