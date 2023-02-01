from collections.abc import Mapping

__all__ = [
    'filter_list', 'find_list', 'merge_list', 'each_list', 'get_list',
    'get_dict', 'del_dict_keys', 'get_deep', 'set_deep', 'merge_dict', 'get_ins_mapping', 'get_dict_mapping', 'get_dict_value_by_type',
    'is_list', 'is_dict', 'slice_str',
    'get_wrap_str', 'is_str',
    'bulk_append_child'
]


# -------------------------------------------list-------------------------------------------
def filter_list(item_list, func, with_index=False):
    """
    Filter the list and return a new list that matches the conditions
    :param with_index:
    :param item_list:
    :param func:
    :return:
    """
    if with_index is True:
        return _filter_list_with_index(item_list, func)

    return list(filter(func, item_list))


def _filter_list_with_index(item_list, func):
    result = []
    for index, item in enumerate(item_list):
        if func(item, index) is True:
            result.append(item)
    return result


def find_list(item_list, func, with_index=False):
    """
    Find an object from the list that matches the conditions
    :param with_index:
    :param item_list:
    :param func:
    :return:
    """
    if with_index is True:
        return _find_list_with_index(item_list, func)

    for item in item_list:
        if func(item) is True:
            return item
    return None


def _find_list_with_index(item_list, func):
    for index, item in enumerate(item_list):
        if func(item, index) is True:
            return item
    return None


def merge_list(lst, *to_merged_list):
    """
    Merge multiple lists into the first list
    :param lst:
    :param to_merged_list:
    :return:
    """
    for item in to_merged_list:
        lst.extend(item)
    return lst


def each_list(item_list, func, with_index=True):
    """
    Iterate each object in the list and execute the callback function
    :param with_index:
    :param item_list:
    :param func:
    :return:
    """
    if with_index is True:
        return _each_list_with_index(item_list, func)

    for item in item_list:
        if func(item) is False:
            return


def _each_list_with_index(item_list, func):
    for index, item in enumerate(item_list):
        if func(item, index) is False:
            return


def get_list(obj, default=None):
    """
    Get the list instance
    -- If obj is a list, just return
    -- If obj is not a list, return default or []
    :param obj:
    :param default:
    :return:
    """
    return obj if is_list(obj) else (default or [])


# -------------------------------------------dict-------------------------------------------
def get_dict(obj, default=None):
    """
     Get the dict instance
    -- If obj is a dict, just return
    -- If obj is not a dict, return default or {}

    :param obj:
    :param default:
    :return:
    """
    return obj if is_dict(obj) else (default or {})


def del_dict_keys(obj, keys):
    """
    Delete the specified keys from the dict object
    :param obj:
    :param keys:
    :return:
    """
    for key in keys:
        obj.pop(key, None)


def get_deep(obj, key, key_split='.', default=None, raising=False):
    """
    Get the deep value of the specified key from the dict object
    :param obj:
    :param key:
    :param key_split:
    :param default:
    :param raising:
    :return:
    """
    value = obj
    try:
        for key in key.split(key_split):
            if isinstance(value, dict):
                value = value[key]
                continue
            else:
                if raising:
                    raise KeyError
                return default
    except KeyError:
        if raising:
            raise
        return default
    else:
        return value


def set_deep(obj, key, value, key_split='.'):
    """
    Set the deep value of the specified key from the dict object
    :param obj:
    :param key:
    :param value:
    :param key_split:
    :return:
    """
    dd = obj
    keys = key.split(key_split)
    latest = keys.pop()
    for k in keys:
        dd = dd.setdefault(k, {})
    dd[latest] = value


def get_ins_mapping(ins_list, attr, deep=False):
    """
    Create a dict map of the specified object list with the specified attribute
    :param ins_list:
    :param attr:
    :param deep:
    :return:
    """
    map_dict = {}
    if deep is True:
        keys = attr.split('.')
        for item in ins_list:
            k_value = item
            for k in keys:
                k_value = getattr(k_value, k)
            map_dict[k_value] = item
    else:
        for item in ins_list:
            map_dict[getattr(item, attr)] = item

    return map_dict


def get_dict_mapping(dict_list, key='id', key_join="+"):
    """
    Create a dict map of the specified dict list withe the specified key
    :param dict_list:
    :param key:
    :param key_join:
    :return:
    """
    map_dict = {}
    for item in dict_list:
        if isinstance(key, list):
            kv = []
            for k_item in key:
                kv.append(str(get_deep(item, k_item)))
            map_dict[key_join.join(kv)] = item
        else:
            map_dict[get_deep(item, key)] = item

    return map_dict


def merge_dict(dct, *merged_dict_list):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merged_dict_list: dct merged into dct
    :return: None
    """
    for dict_item in merged_dict_list:
        for k, v in dict_item.items():  # #2022-04-22 dict_item.iteritems-->dict_item.items
            if (k in dct and isinstance(dct[k], dict)
                    and isinstance(dict_item[k], Mapping)):
                merge_dict(dct[k], dict_item[k])
            else:
                dct[k] = dict_item[k]


def get_dict_value_by_type(obj, key, value_type, default=None, by_instance=False):
    """
    Get the dict value of the specified key, if value is not the instance of the specified type, return default value.

    .. versionadded:: 1.2

    :param obj:
    :param key:
    :param value_type:
    :param default:
    :param by_instance:
    :return:
    """
    if key not in obj:
        return default
    value = obj.get(key)
    if by_instance is True:
        if value_type is int and (value is True or value is False):  # instance(True,input) == True
            return default
        if isinstance(value, value_type):
            return value
    else:
        if type(value) is value_type:
            return value
    return default


# -------------------------------------------type-------------------------------------------
def is_str(value, by_instance=False):
    """
    Check whether the value is string
    :param value:
    :param by_instance:
    :return:
    """
    if by_instance is True:
        return isinstance(value, str)
    return type(value) == str


def is_list(value, by_instance=False):
    """
    Check whether the value is list object
    :param value:
    :param by_instance:
    :return:
    """
    if by_instance is True:
        return isinstance(value, list)
    return type(value) == list


def is_dict(value, by_instance=False):
    """
    Check whether the value is dict object
    :param value:
    :param by_instance:
    :return:
    """
    if by_instance is True:
        return isinstance(value, dict)
    return type(value) == dict


# -------------------------------------------str-------------------------------------------
def get_wrap_str(*items):
    """
    Use '\n' to join multiple strings
    :param items:
    :return:
    """
    result = []
    for item in items:
        if item is not None:
            result.append(str(item))
    return '\n'.join(result)


def slice_str(value, start_len=6, end_len=0, ellipsis_str='......'):
    if end_len != 0:
        end_len = -abs(end_len)

    value = str(value)
    if len(value) <= (start_len - end_len):
        return value
    result = value[0:start_len]
    if end_len != 0:
        result = result + ellipsis_str + value[end_len:]
    return result


# -------------------------------------------other-------------------------------------------
def bulk_append_child(items, parent_map, item_parent_key='parent_id', children_key="children", parent_map_key='id'):
    """
    Append the items to the child list of the matched parent object
    bulk_append_child(interface_items,device_list, 'device_id', 'interface_list')
    :param items:
    :param item_parent_key:
    :param parent_map:
    :param children_key:
    :param parent_map_key:
    :return:
    """
    if not isinstance(items, list):
        items = [items]

    if isinstance(parent_map, list):
        parent_map = get_dict_mapping(parent_map, parent_map_key)

    for item in items:
        parent_attr = item.get(item_parent_key)
        parent_item = parent_map.get(parent_attr)
        if isinstance(parent_item, dict):
            p_children = parent_item[children_key] = parent_item.get(children_key) or []
            p_children.append(item)
