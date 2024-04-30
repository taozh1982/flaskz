from inspect import isfunction

__all__ = ['Attribute', 'cls_to_dict', 'ins_to_dict']


class Attribute:
    """
    Used to create attribute object

    Example:
        obj = AttrCls(**{'a':1,'b':2})
        obj.c = 3
        obj.a = 10

        print(obj.x)
        print(obj)
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, attr):
        return None

    def __repr__(self):
        t = []
        for key, value in self.__dict__.items():
            t.append(key + '=' + str(value))
        return 'Attribute(' + ", ".join(t) + ')'


def cls_to_dict(cls, option=None):  # @2023-03-15 add, convert class(config) to dictionary
    """
    Convert class(config) to dictionary.

     .. versionadded:: 1.5

     Example:
         cls_to_dict(Config)
         cls_to_dict(TestConfig)

    :param cls:
    :param option:
    :return:
    """
    if option is None:
        option = {}
    attr_filter = _get_option_filter(option)

    props = {}
    cls_dir = dir(cls.__class__)
    for key in dir(cls):
        if key.startswith('__') or key in cls_dir:
            continue
        if _filter_attr(cls, key, attr_filter) is False:
            continue

        value = getattr(cls, key)
        if callable(value):
            continue
        props[key] = value

    return props


def ins_to_dict(ins, option=None):
    """
    Convert instance object to dictionary.

    Example:
    ins_to_dict(A, {
        'cascade': 3,  # 如果子项没有cascade，则使用父项-1，如果cascade不大于0，则不对象属性
        'recursion_value': '{...}'
        # 'include': ['a1'],  # 只有include中的字段才会返回，不区分值是否是对象，include的优先级>exclude
        # 'exclude': ['a2'],  # 只有exclude外的字段才会返回，不区分值是否是对象
        # 'getattrs': lambda ins, item_cascade, option, path_keys: ins.__dict__.items(),
        #
        # 'bb': {  # 某个子项的设置
        #     # 'cascade': 1,
        #     # 'include': ['b1'],
        #     'exclude': ['b2'],
        # },
        # 'bb.xx': {  # 子项的子项的设置
        #     'exclude': ['x1']
        # },
        # 'bb.yy': {
        #     'exclude': ['y2']
        # },
        # 'cc': {  # cc列表中的每个数据的设置
        #     'exclude': ['n'],
        #     'cascade': 1
        # },
        # "cc.xx": {
        #     'exclude': ['x2']
        # }
    })

    :param ins:
    :param option:
    :return:
    """
    if isinstance(ins, list):
        result = []
        for item in ins:
            result.append(_ins_to_dict(item, option))
    else:
        result = _ins_to_dict(ins, option)
    return result


def _ins_to_dict(ins, option=None, path_items=None, path_keys=None):
    if path_items is None:
        path_items = []
    else:
        path_items = path_items.copy()
    path_items.append(ins)

    if path_keys is None:
        path_keys = []

    if option is None:
        option = {}

    if len(path_keys) > 0:
        prefix = '.'.join(path_keys)
        item_option = option.get(prefix, {})
    else:
        item_option = option

    if 'cascade' in item_option:
        item_cascade = item_option.get('cascade', 0)
    else:
        item_cascade = _get_option_key(option, path_keys, 'cascade')  # print('查找父option的cascade，直到找到根option')
        if type(item_cascade) == int:
            item_cascade -= len(path_keys)

    if type(item_cascade) is not int:
        item_cascade = 0

    item_relationships = item_option.get('relationships', None)  # @2024-04-14 add
    if type(item_relationships) is not list:
        item_relationships = []

    item_recursion_value = _get_option_key(option, path_keys, 'recursion_value')

    item_getattrs = _get_option_key(option, path_keys, 'getattrs')
    if item_getattrs:
        attrs = item_getattrs(ins, item_cascade, item_relationships, option, path_keys)
    else:
        attrs = ins.__dict__

    # with_none_value = item_option.get('with_none_value', False)
    attr_filter = _get_option_filter(item_option)
    result = {}
    for key, value in attrs.items():
        if _filter_attr(ins, key, attr_filter) is False:
            continue

        _value = None
        if isinstance(value, list):
            _value = []
            _isinstance = False
            for item in value:
                if hasattr(item, '__dict__'):
                    _isinstance = True
                    if item_cascade > 0:
                        if item not in path_items:
                            _value.append(_ins_to_dict(item, option, path_items, path_keys + [key]))
                        elif item_recursion_value is not None:
                            _value.append(item_recursion_value)
                else:
                    _value.append(item)
            if _isinstance is True and len(_value) == 0:
                _value = None
        elif hasattr(value, '__dict__'):
            if item_cascade > 0:
                if value not in path_items:
                    _value = _ins_to_dict(value, option, path_items, path_keys + [key])
                elif item_recursion_value is not None:
                    _value = item_recursion_value
        else:
            _value = value

        # if _value is not None:  # @2024-03-06 remove
        result[key] = _value
        # elif with_none_value:
        #     result[key] = None
    return result


def _get_option_key(option, key_list, key):
    """
    Return the specified value from the option, if not found, search from its parent option until it is found
    """
    if len(key_list) == 0:
        return option.get(key)

    item_key = '.'.join(key_list)
    item_option = option.get(item_key)
    if isinstance(item_option, dict):
        if key in item_option:
            return item_option.get(key)
    return _get_option_key(option, key_list[:-1], key)


def _get_option_filter(option):
    include = option.get('include', [])
    exclude = option.get('exclude', [])

    if isfunction(include):
        has_include = 'func'
    else:
        has_include = len(include) > 0

    if isfunction(exclude):
        has_exclude = 'func'
    else:
        has_exclude = len(exclude) > 0
    return {
        'include': include,
        'has_include': has_include,
        'exclude': exclude,
        'has_exclude': has_exclude,
    }


def _filter_attr(obj, attr, attr_filter):
    has_include = attr_filter.get('has_include')
    include = attr_filter.get('include')
    has_exclude = attr_filter.get('has_exclude')
    exclude = attr_filter.get('exclude')

    if has_include is True and attr not in include:
        return False
    elif has_include == "func" and include(obj, attr) is not True:
        return False

    if has_exclude is True and attr in exclude:
        return False
    elif has_exclude == "func" and exclude(obj, attr) is True:
        return False

    return True
