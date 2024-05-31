import json
from collections.abc import Mapping
from datetime import datetime, date, time
from decimal import Decimal

__all__ = [
    'filter_list', 'find_list', 'merge_list', 'each_list', 'get_list',
    'pop_dict_keys', 'del_dict_keys', 'get_deep', 'set_deep', 'merge_dict', 'get_ins_mapping', 'get_dict_mapping', 'get_dict_value_by_type',
    'get_wrap_str', 'is_str', 'str_replace', 'str_contains_any',
    'is_list', 'is_dict', 'slice_str',
    'json_dumps',
    'bulk_append_child',
    'parse_version'
]


# -------------------------------------------list-------------------------------------------
def filter_list(items, func=None, with_index=False, not_none=False):
    """
    Filter the list and return a new list that matches the conditions
    If func is None and not_none is True, return the not None items.

   .. versionupdated::
        1.6.4 - add not_none param

    Example:
        filter_list(items, not_none=True)
        filter_list(items, lambda item: item is not None)
        filter_list(items, lambda index, item: index > 10 and item is not None, True)

    :param items:
    :param func:
    :param with_index:
    :param not_none:
    :return:
    """
    if func is None and not_none is True:  # @2023-11-20 add
        func = _is_not_none

    if with_index is True:
        return _filter_list_with_index(items, func)

    return list(filter(func, items))


def _filter_list_with_index(items, func):
    result = []
    for index, item in enumerate(items):
        if func(item, index) is True:
            result.append(item)
    return result


def find_list(items, func, with_index=False):
    """
    Find an object from the list that matches the conditions

    Example:
        find_list(items, lambda item: item.get('id') == 10)
        find_list(items, lambda index, item: index > 0 and item.get('id') == 10 , True)

    :param with_index:
    :param items:
    :param func:
    :return:
    """
    if with_index is True:
        return _find_list_with_index(items, func)

    for item in items:
        if func(item) is True:
            return item
    return None


def _find_list_with_index(item_list, func):
    for index, item in enumerate(item_list):
        if func(item, index) is True:
            return item
    return None


def merge_list(target_list, *merged_list):
    """
    Merge multiple lists into the first list

    Example:
        nums = [0, 1]
        merge_list(nums, [2, 3], [4, 5]) # nums = [0, 1, 2, 3, 4, 5]

    :param target_list:
    :param merged_list:
    :return:
    """
    for item in merged_list:
        target_list.extend(item)
    return target_list


def each_list(items, func, with_index=True):
    """
    Iterate each object in the list and execute the callback function

    Example:
        each_list(items, lambda item: item['selected'] = True)

    :param with_index:
    :param items:
    :param func:
    :return:
    """
    if with_index is True:
        return _each_list_with_index(items, func)

    for item in items:
        if func(item) is False:
            return


def _each_list_with_index(items, func):
    for index, item in enumerate(items):
        if func(item, index) is False:
            return


def get_list(items, default=None):
    """
    Get the list instance
    -- If obj is a list, just return
    -- If obj is not a list, return default or []
    :param items:
    :param default:
    :return:
    """
    return items if is_list(items) else (default or [])


# -------------------------------------------dict-------------------------------------------
def pop_dict_keys(d, keys):
    """
    Pop the specified keys from the dict object

    Example:
        pop_dict_keys(a_dict, ['name', 'age'])
        pop_dict_keys(a_dict, 'name')

    :param d:
    :param keys:
    :return:
    """
    if type(keys) is not list:
        keys = [keys]
    result = {}
    for key in keys:
        result[key] = d.pop(key, None)
    return result


del_dict_keys = pop_dict_keys


def get_deep(d: dict, key: str, key_split='.', default=None, raising=False):
    """
    Get the deep value of the specified key from the dict object

    Example:
        get_deep(a_dict, 'address.city')
        get_deep(a_dict, 'address/city', key_split='/')


    :param d:
    :param key:
    :param key_split:
    :param default:
    :param raising:
    :return:
    """
    value = d
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


def set_deep(d: dict, key: str, value, key_split='.'):
    """
    Set the deep value of the specified key from the dict object

    Example:
        set_deep(a_dict, 'address.city', 'New York')
        set_deep(a_dict, 'address/city', 'New York', key_split='/')

    :param d:
    :param key:
    :param value:
    :param key_split:
    :return:
    """
    dd = d
    keys = key.split(key_split)
    latest = keys.pop()
    for k in keys:
        dd = dd.setdefault(k, {})
    dd[latest] = value


def get_ins_mapping(ins_list: list, attr: str, deep=False):
    """
    Create a dict map of the specified object list with the specified attribute

    Example:
        get_ins_mapping([User(name='a'), User(name='b', User(name='c')], 'name')  # {'a':user_c, 'b':user_b, 'c':user_c}

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
                k_value = getattr(k_value, k, None)
            map_dict[k_value] = item
    else:
        for item in ins_list:
            map_dict[getattr(item, attr, None)] = item

    return map_dict


def get_dict_mapping(dict_list: list, key='id', key_join="+"):
    """
    Create a dict map of the specified dict list withe the specified key

    Example:
        get_dict_mapping([{'name': 'a'}, {'name': 'b'}, {'name': 'c'}], 'name')  # {'a':dict_a, 'b':dict_b, 'c':dict_c}


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


def merge_dict(d: dict, *merged_dict_list):
    """
    Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.

    .. versionupdated:: 1.5 - return dct

    Example:
        merge_dict(target_dict, a_dict, b_dict)

    :param d: dict onto which the merge is executed
    :param merged_dict_list: dct merged into dct
    :return: dct
    """
    for dict_item in merged_dict_list:
        for k, v in dict_item.items():  # 2022-04-22 dict_item.iteritems-->dict_item.items
            if (k in d and isinstance(d[k], dict)
                    and isinstance(dict_item[k], Mapping)):
                merge_dict(d[k], dict_item[k])
            else:
                d[k] = dict_item[k]
    return d  # @2023-04-12 add result


def get_dict_value_by_type(d: dict, key: str, value_type, default=None, use_isinstance=False):
    """
    Get the dict value of the specified key, if value is not the instance of the specified type, return default value.

    .. versionadded:: 1.2

    Example
        get_dict_value_by_type(a_dict, 'name', str)
        get_dict_value_by_type(a_dict, 'age', int, 10)

    :param d:
    :param key:
    :param value_type:
    :param default:
    :param use_isinstance:
    :return:
    """
    if key not in d:
        return default
    value = d.get(key)
    if use_isinstance is True:
        if value_type is int and (value is True or value is False):  # instance(True,input) == True
            return default
        if isinstance(value, value_type):
            return value
    else:
        if type(value) is value_type:
            return value
    return default


# -------------------------------------------type-------------------------------------------
def is_str(value, use_isinstance=False):
    """
    Check whether the value is string.

    Example:
        is_str('str') # True
        is_str(1) # False

    :param value:
    :param use_isinstance:
    :return:
    """
    if use_isinstance is True:
        return isinstance(value, str)
    return type(value) == str


def is_list(value, use_isinstance=False):
    """
    Check whether the value is list object.

    Example:
        is_list([]) # True
        is_list('abc') # False

    :param value:
    :param use_isinstance:
    :return:
    """
    if use_isinstance is True:
        return isinstance(value, list)
    return type(value) == list


def is_dict(value, use_isinstance=False):
    """
    Check whether the value is dict object.

    Example:
        is_dict({}) # True
        is_list('abc') # False

    :param value:
    :param use_isinstance:
    :return:
    """
    if use_isinstance is True:
        return isinstance(value, dict)
    return type(value) == dict


# -------------------------------------------str-------------------------------------------

def get_wrap_str(*items):
    """
    Use '\n' to join multiple strings.

    :param items:
    :return:
    """
    result = []
    for item in items:
        if item is not None:
            result.append(str(item))
    return '\n'.join(result)


def slice_str(string, start_len=6, end_len=0, ellipsis_str='......'):
    if end_len != 0:
        end_len = -abs(end_len)

    string = str(string)
    if len(string) <= (start_len - end_len):
        return string
    result = string[0:start_len]
    if end_len != 0:
        result = result + ellipsis_str + string[end_len:]
    return result


def str_replace(string, old, new=''):
    """
    Return a copy with all occurrences of substring old replaced by new.

    .. versionadded:: 1.5

    Example:
        str_replace('abca','a','A')             # AbcA
        str_replace('abca',{'a':'A','b':'B'})   # ABcA
        str_replace('abca',['a','b'],"*")       # **c*

    :param string:
    :param old:
    :param new:
    :return:
    """
    v_type = type(old)
    if v_type is dict:
        for key in old:
            string = string.replace(key, old[key])
    elif v_type is list:
        for item in old:
            string = string.replace(item, new)
    else:
        string = string.replace(old, new)
    return string


def str_contains_any(string, substrings):
    """
    Check whether any substring is in the specified string.

    Example:
        str_contains_any('Cisco Nexus Operating System', ['Cisco', 'Nexus']) # True

    :param string: the specified string
    :param substrings: the substring list
    :return:
    """
    return any(sub in string for sub in substrings)


# -------------------------------------------other-------------------------------------------
def bulk_append_child(items, parents, item_parent_key='parent_id', children_key="children", parent_map_key='id'):
    """
    Append the items to the child list of the matched parent object.

    Example:
        bulk_append_child(interface_items,device_list, 'device_id', 'interface_list')

    :param items:
    :param item_parent_key:
    :param parents:
    :param children_key:
    :param parent_map_key:
    :return:
    """
    if not isinstance(items, list):
        items = [items]

    if isinstance(parents, list):
        parents = get_dict_mapping(parents, parent_map_key)

    for item in items:
        parent_attr = item.get(item_parent_key)
        parent_item = parents.get(parent_attr)
        if isinstance(parent_item, dict):
            p_children = parent_item[children_key] = parent_item.get(children_key) or []
            p_children.append(item)


def parse_version(version):
    """
    Parse version string to int list, if version is integer, it will be converted to int

    Example:
        parse_version(sqlalchemy.__version__)   # --> [2, 0, 20] / [2, 0, '0rc1']

    :param version: the version to be parsed, str/int/float/package
    """
    version_type = type(version)

    if version_type is int:  # 1-->1
        return [version]

    if version_type is float:  # 1.2-->[1,2]
        version = str(version)
    elif version_type is not str:  # sqlalchemy,sys
        version = getattr(version, '__version__', None) or getattr(version, 'version', None)

    if type(version) is not str:
        return []

    versions = []
    for v in version.split('.'):
        if v.isdigit():
            versions.append(int(v))
        else:
            versions.append(v)
    return versions


# -------------------------------------------json-------------------------------------------
def json_dumps(obj, **kwargs):
    """
    Serialize obj to a JSON formatted string, with support for additional data types.
    The function extends the default JSON serialization capabilities of Python's json module by
    providing custom serialization for types that are not natively supported,
    such as datetime, date, time, Decimal, bytes, bytearray, set, and custom objects.

    .. versionadded:: 1.8.0

    Example:
        json_dumps({
            'str': 'example',
            'integer': 1,
            'float': 3.14,
            'boolean': True,
            'none': None,
            'list': [1, 2, 3],
            'dict': {'key': 'value'},
            'tuple': (1, 2, 3),

            'set': {1, 2, 3},
            'datetime': datetime.now(),
            'date': date.today(),
            'time': datetime.now().time(),
            'decimal': Decimal('10.5'),
            'bytes': b'byte data',
            'bytearray': bytearray(b'bytearray data')
        }, indent=4)
    :param obj:
    :return:
    """
    if 'default' not in kwargs:
        kwargs['default'] = _json_serializer
    return json.dumps(obj, **kwargs)


def _json_serializer(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, (Decimal, bytes, bytearray)):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f"Object of type '{obj.__class__.__name__}' is not JSON serializable")


# -------------------------------------------private-------------------------------------------
def _is_not_none(item, *args, **kwargs):
    return item is not None
