from flask import request
from sqlalchemy import desc, asc, Column
from sqlalchemy.sql.elements import UnaryExpression

from ._common import get_dict, is_str, is_dict, is_list

__all__ = ['get_remote_addr', 'is_ajax', 'get_request_json', 'get_pss']


def get_remote_addr():
    """
    Get the remote ip address.

    :return:
    """
    if request:
        return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)


def is_ajax():
    """
    Check if the request is an ajax request.
    :return:
    """
    if request:
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    return False


def get_request_json(*args):
    """
    Get the JSON data(parsed) in request.
    If json does not exist or parsing json error, return {}

    .. versionadded:: 1.3

    :return:
    """
    data = None
    try:
        data = request.get_json(force=True, silent=True)
    except Exception:
        pass
    if data is None:
        if len(args) > 0:
            return args[0]
    return data


def get_pss(cls, pss_config=None):
    """
    Get the search, sort and paging information.
    pss = page+search+sort

    Example:
        result, result = TemplateModel.query_pss(get_pss(   # use flaskz.utils.get_pss to format condition
            TemplateModel, {   # FROM templates
                "search": {                         # WHERE
                    "like": "t",                    # name like '%t%' OR description like '%t%' (TemplateModel.like_columns = ['name', description])
                    "age": {                        # AND (age>1 AND age<20)
                        ">": 1,                     # operator:value, operators)'='/'>'/'<'/'>='/'<='/'BETWEEN'/'LIKE'/'IN'
                        "<": 20
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
    ands = []
    ors = []
    search_like = search.pop('like', None)
    like_columns = getattr(cls, 'like_columns', None)
    likes = []
    if search_like and like_columns is not None:
        search_like = str(search_like).strip()
        if search_like != '':
            for col in like_columns:
                if is_str(col):
                    col_field = col
                else:
                    col_field = cls.get_column_field(col)
                likes.append(col_field + " like '%" + search_like + "%'")

    columns_fields = cls.get_columns_fields()
    _ands = search.pop('_ands', None)
    if _ands:
        for key in _ands:
            _append_item(ands, key, _ands[key], columns_fields)

    _ors = search.pop('_ors', None)
    if _ors:
        for key in _ors:
            _append_item(ors, key, _ors[key], columns_fields)

    for key in search:
        _append_item(ands, key, search[key], columns_fields)
    # --------------------page--------------------
    page = pss_config.get('page') or {}
    offset = page.get('offset') or page.get('skip') or 0
    limit = page.get('limit') or page.get('size') or 100000

    # --------------------sort--------------------
    # @2022-04-10 fix exception subs2 = relationship('PerfTestSubModel2', cascade='all,delete-orphan', lazy='joined') ->
    # Can't resolve label reference for ORDER BY / GROUP BY / DISTINCT etc. Textual SQL expression 'f2' should be explicitly declared as text('f2')
    sort = pss_config.get('sort')
    sorts = []
    if is_list(sort):
        sorts = sort
    elif is_dict(sort):
        sorts = [sort]

    orders = []
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

    # order = None
    # _order = sort.get('order')
    # if _order and not is_str(_order):  # desc(Model.column)
    #     order = _order
    # else:
    #     sort_field = sort.get('field')
    #     if sort_field:
    #         sort_column = cls.get_column_by_field(sort_field)
    #         if sort_column is not None:
    #             if _order and str(_order).strip().lower() in ['desc', 'descend', 'descending']:
    #                 order = desc(sort_column)
    #
    #             if order is None:
    #                 order = asc(sort_column)  # default is asc.

    return {
        'filter_ands': ands,
        'filter_ors': ors,
        'filter_likes': likes,
        'offset': offset,
        'limit': limit,
        'order': orders,
    }


def _append_item(items, key, value, columns_fields):  # @2023-02-06 add columns_fields args to fix "Unknown column 'col' in 'where clause'"
    if columns_fields and (key not in columns_fields):
        return items

    if value is not None:
        if is_str(value):
            value = value.strip()
            if value != '':
                val_arr = value.split('||')
                for op_v in val_arr:
                    items.append(key + "='" + op_v + "'")
        elif is_dict(value):
            for operator, op_v in value.items():
                items.append(key + operator + str(op_v))
        else:
            items.append(key + '=' + str(value))
    return items
