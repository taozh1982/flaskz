"""
only for internal use
"""


def get_dict(d, default=None):
    """
     Get the dict instance
    -- If obj is a dict, just return
    -- If obj is not a dict, return default or {}

    :param d:
    :param default:
    :return:
    """
    return d if type(d) == dict else (default or {})
