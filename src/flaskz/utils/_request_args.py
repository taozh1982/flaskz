from flask import request
from sqlalchemy import desc, asc

from ._common import get_dict, is_str, is_dict

__all__ = ['get_remote_addr', 'is_ajax', 'get_request_json', 'get_pss']


def get_remote_addr():
    """
    Get the remote ip address.
    :return:
    """
    return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)


def is_ajax():
    """
    Check if the request is an ajax request.
    :return:
    """
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def get_request_json(*args):
    """
    Get the JSON data(parsed) in request
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
    :param cls:
    :param pss_config:
    :return:
    """
    pss_config = get_dict(pss_config)
    search = pss_config.get('search') or {}
    sort = pss_config.get('sort') or {}
    page = pss_config.get('page') or {}
    # --------------------search--------------------
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
    offset = page.get('offset') or page.get('skip') or 0
    limit = page.get('limit') or page.get('size') or 100000

    # --------------------sort--------------------
    # sort_field = sort.get('field')
    # order = sort.get('order')
    #
    # if order and sort_field:
    #     order = str(order).strip().lower()
    #     if order in ['desc', 'descend', 'descending']:
    #         order = desc(sort_field)  # default is desc.
    #     else:
    #         order = asc(sort_field)
    # elif sort_field:
    #     if is_str(sort_field):
    #         order = asc(sort_field)
    #     else:
    #         order = sort_field
    # else:
    #     order = None

    # @2022-04-10 fix exception subs2 = relationship('PerfTestSubModel2', cascade='all,delete-orphan', lazy='joined') ->
    # Can't resolve label reference for ORDER BY / GROUP BY / DISTINCT etc. Textual SQL expression 'f2' should be explicitly declared as text('f2')

    order = None
    _order = sort.get('order')
    if _order and not is_str(_order):  # desc(Model.column)
        order = _order
    else:
        sort_field = sort.get('field')
        if sort_field:
            sort_column = cls.get_column_by_field(sort_field)
            if sort_column is not None:
                if _order and str(_order).strip().lower() in ['desc', 'descend', 'descending']:
                    order = desc(sort_column)

                if order is None:
                    order = asc(sort_column)  # default is asc.

    return {
        'filter_ands': ands,
        'filter_ors': ors,
        'filter_likes': likes,
        'offset': offset,
        'limit': limit,
        'order': order,
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
