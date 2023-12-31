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


def contains_any(collection, targets):
    """
    Checks whether the collection contains any item

    :param collection:
    :param targets:
    :return:
    """
    collection_type = type(collection)
    if collection_type is dict:
        return any(key in collection for key in targets)
    elif collection_type is list:
        return any(element in collection for element in targets)
    return False


def vie(condition, true_value, false_value):
    """
    If condition is True value return true_value, else return false_value
    False/None/0/''/()/{}/[] is false value

    :param condition:
    :param true_value:
    :param false_value:
    :return:
    """
    return true_value if condition else false_value
