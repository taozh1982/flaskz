import math
import time

from flask import current_app, g

from ._common import is_dict

__all__ = ['set_app_cache', 'get_app_cache', 'clear_app_cache', 'set_g_cache', 'get_g_cache', 'remove_g_cache']


def _generate_cache_expire_data(data, expire_minutes=0):
    if type(expire_minutes) == int and expire_minutes > 0:
        data = {
            '_zexpires_time': math.floor(expire_minutes * 60 + time.time()),
            'data': data,
        }
    return data


def set_app_cache(key, data, expire_minutes=0):
    """
    Set the current application data cache, such as menu items
    :param expire_minutes:
    :param key:
    :param data:
    :return:
    """
    cache = getattr(current_app, 'z_data_cache', None)
    if cache is None:
        cache = current_app.z_data_cache = {}
    cache[key] = _generate_cache_expire_data(data, expire_minutes)


def get_app_cache(key):
    """
    Get the current application data cache by the key.
    :param key:
    :return:
    """
    cache = getattr(current_app, 'z_data_cache', None)
    if cache:
        data = cache.get(key)
        if is_dict(data) and '_zexpires_time' in data:
            if data.get('_zexpires_time') < time.time():
                return None
            return data.get('data')
        return data

    return None


def clear_app_cache():
    """
    Clear all the current application data caches.
    :return:
    """
    cache = getattr(current_app, 'z_data_cache', None)
    if cache:
        cache.clear()


def set_g_cache(key, data):
    """
    Set the data cache in g, such as db session.
    :param key:
    :param data:
    :return:
    """
    cache = getattr(g, 'z_data_cache', None)
    if cache is None:
        cache = g.z_data_cache = {}
    cache[key] = data


def get_g_cache(key):
    """
    Get the g data cache by the key.
    :param key:
    :return:
    """
    cache = getattr(g, 'z_data_cache', None)
    if cache:
        return cache.get(key)
    return None


def remove_g_cache(key):
    """
    Remove the g data cache.
    :param key:
    :return:
    """
    cache = getattr(g, 'z_data_cache', None)
    if cache:
        del cache[key]
