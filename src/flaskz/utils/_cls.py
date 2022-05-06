from inspect import isfunction

__all__ = ['Attribute', 'ins_to_dict']


class Attribute:
    """
    Used to create attribute object
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


def ins_to_dict(ins, option=None):
    """
    Convert instance object to dictionary
    ex)
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

    if type(item_cascade) != int:
        item_cascade = 0

    item_recursion_value = _get_option_key(option, path_keys, 'recursion_value')

    item_getattrs = _get_option_key(option, path_keys, 'getattrs')
    if item_getattrs:
        attrs = item_getattrs(ins, item_cascade, option, path_keys)
    else:
        attrs = ins.__dict__

    item_include = item_option.get('include', [])
    item_exclude = item_option.get('exclude', [])

    if isfunction(item_include):
        has_item_include = 'func'
    else:
        has_item_include = len(item_include) > 0

    if isfunction(item_exclude):
        has_item_exclude = 'func'
    else:
        has_item_exclude = len(item_exclude) > 0

    result = {}

    # with_none_value = item_option.get('with_none_value', False)

    for key, value in attrs.items():

        if has_item_include is True and key not in item_include:
            continue
        elif has_item_include == "func" and item_include(ins, key) is not True:
            continue

        if has_item_exclude is True and key in item_exclude:
            continue
        elif has_item_exclude == "func" and item_exclude(ins, key) is True:
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

        if _value is not None:
            result[key] = _value
        # elif with_none_value:
        #     result[key] = None
    return result


def _get_option_key(option, key_list, key):
    """
    查找父option的cascade，直到找到根option
    """
    if len(key_list) == 0:
        return option.get(key)

    item_key = '.'.join(key_list)
    item_option = option.get(item_key)
    if isinstance(item_option, dict):
        if key in item_option:
            return item_option.get(key)
    return _get_option_key(option, key_list[:-1], key)
