from sqlalchemy import desc, asc, Column
from sqlalchemy.sql.elements import UnaryExpression

__all__ = ['parse_pss']


def parse_pss(cls, pss_config=None):
    """
    Get the search, sort and paging information.
    flaskz.utils.get_pss == flaskz.models.parse_pss
    pss = page+search+sort

    .. versionadded:: 1.6.1 - rename flaskz.utils.get_pss function to flaskz.models.parse_pss, flaskz.utils.get_pss is still available
    .. versionupdated:: 1.6.1 - change return list item(avoid SQL injection): SQL text --> Column.operator(parameter)  ex) "name like '%admin%'" --> TemplateModel.name.like('%admin%')

    Example:
        result, result = TemplateModel.query_pss(get_pss(   # use flaskz.utils.get_pss to format condition
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
    :param pss_config: page+search+sort
    :return:
    """
    pss_config = get_dict(pss_config)
    # --------------------search--------------------
    search = pss_config.get('search') or {}

    likes = _get_search_like_filters(cls, search.pop('like', None), search.pop('ilike', None))

    ands = []
    ors = []
    _ands = search.pop('_ands', None)
    if _ands:
        for key in _ands:
            _append_search_filters(ands, cls, key, _ands[key])

    _ors = search.pop('_ors', None)
    if _ors:
        for key in _ors:
            _append_search_filters(ors, cls, key, _ors[key])

    for key in search:
        _append_search_filters(ands, cls, key, search[key])

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
    groups = _get_groups(cls, pss_config.get('group', None))  # @2023-06-07 add

    # --------------------page--------------------
    page = pss_config.get('page') or {}
    offset = page.get('offset') or page.get('skip') or 0
    limit = page.get('limit') or page.get('size') or 100000

    # --------------------sort--------------------
    # @2022-04-10 fix exception subs2 = relationship('PerfTestSubModel2', cascade='all,delete-orphan', lazy='joined') ->
    # Can't resolve label reference for ORDER BY / GROUP BY / DISTINCT etc. Textual SQL expression 'f2' should be explicitly declared as text('f2')
    orders = _get_sorts(cls, pss_config.get('sort', None))

    return {
        'filter_ands': _filter_pss_list(ands),
        'filter_ors': _filter_pss_list(ors),
        'filter_likes': _filter_pss_list(likes),

        'order': _filter_pss_list(orders),
        'group': _filter_pss_list(groups),

        'offset': offset,
        'limit': limit
        # 'distinct': distinct
    }


def _filter_pss_list(items):
    return [item for item in items if item is not None]


def _get_groups(cls, group):
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


def _get_sorts(cls, sort):
    """
    Get sort list.
    """
    orders = []
    sorts = []
    if is_list(sort):
        sorts = sort
    else:  # @2023-08-31 elif is_dict(sort):-->else
        sorts = [sort]

    for sort_item in sorts:
        if sort_item is None or sort_item == '':
            continue

        if is_str(sort_item):  # sort: "name"/["name"...]
            sort_column = cls.get_column_by_field(sort_item)
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
                    sort_column = cls.get_column_by_field(sort_field)
                    if sort_column is not None:
                        if _order and str(_order).strip().lower() in ['desc', 'descend', 'descending']:  # {"field": "name", "order": "desc"}
                            orders.append(desc(sort_column))
                        else:
                            orders.append(asc(sort_column))  # {"field": "name"}.
    return orders


def _get_search_like_filters(cls, search_like, search_ilike):
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


def _append_search_filters(items, cls, key, value):
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
                val_arr = value.split('||')
                for op_v in val_arr:
                    items.append(get_col_op(col, '==', op_v))
        elif is_dict(value):
            for operator, op_v in value.items():
                items.append(get_col_op(col, operator, op_v))
        else:
            items.append(get_col_op(col, '==', value))
    return items


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


from ..utils import get_dict, is_str, is_dict, is_list
