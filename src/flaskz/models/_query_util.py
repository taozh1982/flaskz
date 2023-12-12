from sqlalchemy import desc, asc, Column
from sqlalchemy.sql.elements import UnaryExpression

__all__ = ['parse_pss']


def parse_pss(cls, pss_payload=None):
    """
    Get the search, sort and paging information.
    flaskz.utils.get_pss == flaskz.models.parse_pss
    pss = page+search+sort

    .. versionadded:: 1.6.1 - rename flaskz.utils.get_pss function to flaskz.models.parse_pss, flaskz.utils.get_pss is still available
    .. versionupdated::
        - 1.6.1: change return list item(avoid SQL injection): SQL text --> Column.operator(parameter)  ex) "name like '%admin%'" --> TemplateModel.name.like('%admin%')
        - 1.6.5: add relation search and page

    Example:
        result, result = TemplateModel.query_pss(parse_pss(   # use flaskz.models.parse_pss to parse pss payload
            TemplateModel, {   # FROM templates
                "search": {                         # WHERE
                    "like": "t",                    # name like '%t%' OR description like '%t%' (TemplateModel.like_columns = ['name', description])
                    "age": {                        # AND (age>1 AND age<20)
                        ">": 1,                     # operator:value, operators)'='/'>'/'<'/'>='/'<='/'BETWEEN'/'LIKE'/'IN'
                        "<": 20
                    },
                   "city": {                        # AND (city IN ('Paris','London'))
                        "in": ['Paris' ,'London'],
                    },
                    # "address.city": "New York",   # *relation
                    "email": "taozh@focus-ui.com",  # AND (email='taozh@focus-ui.com')
                    "_ors": {                       # AND (country='America' OR country='Canada')
                        "country": "America||Canada"
                    },
                    "_ands": {                      # AND (grade>1 AND grade<5)
                        "grade": {
                            ">": 1,
                            "<": 5
                        }
                    }
                },
                "sort": {                           # ORDER BY templates.name ASC
                    "field": "name",
                    "order": "asc"
                },
                # "sort":[                            # multiple sort
                #     {"field": "name", "order": "asc"},
                #     {field": "age", "order": "desc"}
                # ],
                "page": {                           # LIMIT ? OFFSET ? (20, 0)
                    "offset": 0,
                    "size": 20
                }
            }))

    :param cls: Model class
    :param pss_payload: page+search+sort
    :return:
    """
    pss_payload = get_dict(pss_payload)
    # --------------------search--------------------
    search = pss_payload.get('search') or pss_payload.get('query') or {}
    parse_option = {
        'str_sep': _get_str_value_sep(cls, search)
    }
    pss_options = {}
    pss_options.update(_parse_search_filters(cls, search, parse_option))
    relationships_pss = _parse_relationships_search_filters(cls, pss_payload, parse_option)  # @2023-12-05 add relationship search
    # distinct = []  # @2023-06-07 add
    # _distinct = search.pop('_distinct', None)
    # if _distinct:
    #     if is_str(_distinct):
    #         _distinct = [_distinct]
    #
    #     if is_list(_distinct):
    #         for distinct_item in _distinct:
    #             distinct_column = cls.get_column_by_field(distinct_item)
    #             if distinct_column is not None:
    #                 distinct.append(distinct_column)

    # --------------------group--------------------
    groups = _parse_groups(cls, pss_payload.get('group', None))  # @2023-06-07 add

    # --------------------page--------------------
    page = pss_payload.get('page') or {}
    offset = page.get('offset') or page.get('skip') or 0
    limit = page.get('limit') or page.get('size')  # @2023-11-22 remove 'or 100000'

    # --------------------sort--------------------
    # @2022-04-10 fix exception subs2 = relationship('PerfTestSubModel2', cascade='all,delete-orphan', lazy='joined') ->
    # Can't resolve label reference for ORDER BY / GROUP BY / DISTINCT etc. Textual SQL expression 'f2' should be explicitly declared as text('f2')
    orders = _parse_sorts(cls, pss_payload.get('sort'))

    pss_options.update({
        'order': _filter_pss_list(orders),
        'group': _filter_pss_list(groups),

        'offset': offset,
        'limit': limit,

        'relationships': relationships_pss
        # 'distinct': distinct
    })
    return pss_options


# -------------------------------------------search-------------------------------------------
def _parse_search_filters(cls, search, parse_option):
    """
    Get the search options
    """
    # --------------------search--------------------
    # search = search or {}
    # @2023-12-05 add _like & _ilike
    search_like = _get_first_non_column_field_value(cls, search, ['_like', 'like'])
    search_ilike = _get_first_non_column_field_value(cls, search, ['_ilike', 'ilike'])
    likes = _parse_search_like_filters(cls, search_like, search_ilike)
    ands = []
    ors = []
    str_sep = parse_option.get('str_sep')

    _ands = _get_first_non_column_field_value(cls, search, ['_ands', 'ands'])  # search.pop('_ands', None)
    if _ands:
        for key in _ands:
            _append_search_filters(ands, cls, key, _ands[key], str_sep)
    _ors = _get_first_non_column_field_value(cls, search, ['_ors', 'ors'])  # search.pop('_ors', None)
    if _ors:
        for key in _ors:
            _append_search_filters(ors, cls, key, _ors[key], str_sep)

    for key in search:
        _append_search_filters(ands, cls, key, search[key], str_sep)

    return {
        'filter_ands': _filter_pss_list(ands),
        'filter_ors': _filter_pss_list(ors),
        'filter_likes': _filter_pss_list(likes),
    }


def _get_first_non_column_field_value(cls, props, fields):
    """
    Get the value of the first non-column field in the specified dictionary
    """
    for field in fields:
        if field in props and cls.get_column_by_field(field) is None:
            return props.get(field)


def _get_str_value_sep(cls, search_config):
    """
    Get the separator of string type value
    """
    sep_keys = ['_str_sep', 'str_sep']
    if not contains_any(search_config, sep_keys):
        return '||'
    return _get_first_non_column_field_value(cls, search_config, sep_keys)


def _parse_search_like_filters(cls, search_like, search_ilike):
    """
    Get like list by like_columns.
    """
    like_filters = []

    like_columns = []
    for col in getattr(cls, 'like_columns', []):
        if is_str(col):
            col = cls.get_column_by_field(col)
        if col is not None:
            like_columns.append(col)
    if len(like_columns) == 0:
        return like_filters

    if search_like is not None and search_like != '':
        if not (search_like.startswith('%') or search_like.startswith('%')):
            search_like = "%" + search_like + "%"
        for col in like_columns:
            like_filters.append(get_col_op(col, 'like', search_like))

    if search_ilike is not None and search_ilike != '':
        if not (search_ilike.startswith('%') or search_ilike.startswith('%')):
            search_ilike = "%" + search_ilike + "%"
        for col in like_columns:
            like_filters.append(get_col_op(col, 'ilike', search_ilike))
    return like_filters


def _append_search_filters(items, cls, key, value, str_sep='||'):
    """
    Append filter item
    """
    col = cls.get_column_by_field(key)
    if col is None:
        return items

    if value is not None:
        if is_str(value):
            value = value.strip()
            if value != '':
                if str_sep:
                    val_arr = value.split(str_sep)
                    for op_v in val_arr:
                        items.append(get_col_op(col, '==', op_v))
                else:
                    items.append(get_col_op(col, '==', value))
        elif is_dict(value):
            for operator, op_v in value.items():
                items.append(get_col_op(col, operator, op_v))
        else:
            items.append(get_col_op(col, '==', value))
    return items


def _parse_relationships_search_filters(cls, pss_payload, parse_option):
    """
    Returns pss config of the relationships

    :param cls:
    :param pss_payload:
    :return:
    """
    # @2023-12-05 add
    relationships = cls.get_relationships()
    relationships_filters = {}
    search = pss_payload.get('search') or {}

    relationships_search = {}  # Role:{'name':'admin'}
    for key, value in search.items():  # "role.name":"admin"
        col = cls.get_column_by_field(key)
        if col is not None:
            continue
        keys = key.split('.')
        if len(keys) == 2:
            relationship_key = keys[0]
            relationship_filed = keys[1]
            relationship = relationships.get(relationship_key)
            if relationship:
                relationship_cls = relationship.mapper.class_
                relationships_search.setdefault(relationship_cls, {}).update({relationship_filed: value})
    for key in relationships.keys():  # "role":{"name":"admin","like":"administrator"}
        col = cls.get_column_by_field(key)
        if col is not None:
            continue
        relationship_search_value = search.get(key, None)
        if type(relationship_search_value) is dict:
            relationship_cls = relationships[key].mapper.class_
            relationships_search.setdefault(relationship_cls, {}).update(relationship_search_value)

    for relationship_cls, relationship_search in relationships_search.items():
        relationships_filters[relationship_cls] = _parse_search_filters(relationship_cls, relationship_search, parse_option)

    return relationships_filters


def get_col_op(column, operator, value):
    """
        < , <= , == , != , > , >=
        in , notin , between ,
        is , isnot
        like , ilike , notlike , notilike

        ~startswith , endswith , contains~
    """
    operator = operator.lower()
    op_func_mapping = {
        'in': lambda col, val: col.in_(val) if type(val) is list else None,
        'notin': lambda col, val: col.notin_(val) if type(val) is list else None,
        'between': lambda col, val: col.between(*val) if type(val) is list else None,

        'is': lambda col, val: col.is_(val),
        'isnot': lambda col, val: col.is_not(val),

        'like': lambda col, val: col.like(val),
        'ilike': lambda col, val: col.ilike(val),
        'notlike': lambda col, val: col.notlike(val),
        'notilike': lambda col, val: col.notilike(val),

        '==': lambda col, val: col.__eq__(val)
    }
    if operator in op_func_mapping:
        return op_func_mapping.get(operator)(column, value)
    return column.op(operator)(value)


def _filter_pss_list(items):
    return [item for item in items if item is not None]


# -------------------------------------------sort+group-------------------------------------------
def _parse_groups(cls, group):
    """
    Get group by list
    """
    groups = []
    if group:
        if is_str(group):
            group = [group]
        if is_list(group):
            for group_item in group:
                group_column = cls.get_column_by_field(group_item)
                if group_column is not None:
                    groups.append(group_column)
    return groups


def _parse_sorts(cls, sort):
    """
    Get sort list.
    @2023-12-05 add relationship sort
    """
    orders = []
    if is_list(sort):
        sorts = sort
    else:  # @2023-08-31 elif is_dict(sort):-->else
        sorts = [sort]

    for sort_item in sorts:
        if sort_item is None or sort_item == '':
            continue

        if is_str(sort_item):  # sort: "name"/["name"...]  'role.name'
            sort_column = _get_column_by_field(cls, sort_item)
            if sort_column is not None:
                orders.append(asc(sort_column))
        elif type(sort_item) is Column:  # User.name
            if sort_item in cls.get_columns():
                orders.append(asc(sort_item))
        elif type(sort_item) is UnaryExpression:  # desc(User.name)/asc(User.name)
            orders.append(sort_item)
        elif is_dict(sort_item):  # {"field": "name", "order": "desc"}
            _order = sort_item.get('order')
            if _order and not is_str(_order):  # {"order": desc(User.name))} == "sort":desc(User.name)
                orders.append(_order)
            else:
                sort_field = sort_item.get('field')  # {"field": "name", "order": "asc"}
                if sort_field:
                    sort_column = _get_column_by_field(cls, sort_field)
                    if sort_column is not None:
                        if _order and str(_order).strip().lower() in ['desc', 'descend', 'descending']:  # {"field": "name", "order": "desc"}
                            orders.append(desc(sort_column))
                        else:
                            orders.append(asc(sort_column))  # {"field": "name"}.
    return orders


def _get_column_by_field(cls, field, include_relationship=True):
    """
    Get the column of the specified class according to the field
    if not found in class and include_relationship==True, return the column of the relationship class
    """
    sort_column = cls.get_column_by_field(field)
    if include_relationship is True and sort_column is None:
        keys = field.split('.')
        if len(keys) == 2:
            relationships = cls.get_relationships()
            relationship_key = keys[0]
            relationship_filed = keys[1]
            relationship = relationships.get(relationship_key)
            if relationship:
                relationship_cls = relationship.mapper.class_
                sort_column = relationship_cls.get_column_by_field(relationship_filed)
    return sort_column


from ..utils import is_str, is_dict, is_list
from ..utils._private import get_dict, contains_any
