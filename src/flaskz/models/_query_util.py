from sqlalchemy import desc, asc, Column, and_, or_
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
        - 1.7.0: add relationship-related search and sort parameter parsing
        - 1.7.2: add like_columns parameter parsing

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
                    # "address": {                  # *relation like
                    #     "like": True,
                    #     "like_columns": ["city"]  # like columns of the relation
                    # },
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
    parse_option = _get_parse_options(cls, pss_payload)
    pss_options = {}
    pss_options.update(_parse_search_filters(cls, search, parse_option))
    relationships_pss = _parse_relationships_search_filters(cls, pss_payload, pss_options, parse_option)  # @2023-12-05 add relationship search
    _merge_search_filter_likes(pss_options, parse_option)
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
    limit = page.get('limit') or page.get('size') or 100000  # @2023-11-22 remove 'or 100000'

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

    like_filters, ilike_filters, notlike_filters, notilike_filters = _parse_search_like_filters(cls, search, *_get_search_like_values(cls, search))
    ands = []
    ors = []

    search_ands_field, search_ands = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('ands'))  # search.pop('_ands', None)
    if search_ands:
        for key in search_ands:
            _append_search_filters(ands, cls, key, search_ands[key], parse_option)
    search_ors_field, search_ors = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('ors'))  # search.pop('_ors', None)
    if search_ors:
        for key in search_ors:
            _append_search_filters(ors, cls, key, search_ors[key], parse_option)

    for key in search:
        _append_search_filters(ands, cls, key, search[key], parse_option)

    return {
        'filter_ands': _filter_pss_list(ands),
        'filter_ors': _filter_pss_list(ors),

        'filter_likes': _filter_pss_list(like_filters),
        'filter_ilikes': _filter_pss_list(ilike_filters),
        'filter_notlikes': _filter_pss_list(notlike_filters),
        'filter_notilikes': _filter_pss_list(notilike_filters),
    }


def _parse_relationships_search_filters(cls, pss_payload, pss_options, parse_option):
    """
    Returns pss config of the relationships

    .. versionupdated::
        - 1.8.2: change the key of relationships_filters to InstrumentedAttribute

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
                relationships_search.setdefault(relationship, {}).update({relationship_filed: value})
    for key in relationships.keys():  # "role":{"name":"admin","like":"administrator"}
        col = cls.get_column_by_field(key)  # ?
        if col is not None:
            continue
        relationship_search_value = search.get(key, None)
        if type(relationship_search_value) is dict:
            relationship = relationships.get(key)
            relationships_search.setdefault(relationship, {}).update(relationship_search_value)

    cls_search_like, cls_search_ilike, cls_search_notlike, cls_search_notilike = _get_search_like_values(cls, search)
    for relationship, relationship_search_payload in relationships_search.items():
        # @2023-12-12 add
        # Merge into global like query
        relationship_cls = relationship.mapper.class_
        relationship_search = dict(relationship_search_payload)
        (search_like_field, search_like), (
            search_ilike_field, search_ilike), (
            search_notlike_field, search_notlike), (
            search_notilike_field, search_notilike) = _get_search_like_values(relationship_cls, relationship_search, True)
        if search_like is True:
            relationship_search[search_like_field] = cls_search_like
        if search_ilike is True:
            relationship_search[search_ilike_field] = cls_search_ilike
        if search_notlike is True:
            relationship_search[search_notlike_field] = cls_search_notlike
        if search_notilike is True:
            relationship_search[search_notilike_field] = cls_search_notilike

        relationship_pss_options = _parse_search_filters(relationship_cls, relationship_search, parse_option)
        relationships_filters[getattr(cls, relationship.key)] = relationship_pss_options  # @2025-06-18 RelationshipProperty --> InstrumentedAttribute

        if search_like is True:
            pss_options.setdefault('filter_likes', []).extend(relationship_pss_options.pop('filter_likes', []))
        if search_ilike is True:
            pss_options.setdefault('filter_ilikes', []).extend(relationship_pss_options.pop('filter_ilikes', []))
        if search_notlike is True:
            pss_options.setdefault('filter_notlikes', []).extend(relationship_pss_options.pop('filter_notlikes', []))
        if search_notilike is True:
            pss_options.setdefault('filter_notilikes', []).extend(relationship_pss_options.pop('filter_notilikes', []))

        _merge_search_filter_likes(relationship_pss_options, parse_option)

    return relationships_filters


def _append_search_filters(items, cls, key, value, parse_option):
    """
    Append filter item
    """
    col = cls.get_column_by_field(key)
    if col is None:
        return items
    ignore_null = parse_option.get('ignore_null')
    str_sep = parse_option.get('str_sep')
    if value is not None or ignore_null is False:
        if is_str(value):
            # value = value.strip()  # @2023-12-12 remove
            if value != '' or ignore_null is False:
                if str_sep and value != str_sep:
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
    value = _get_operator_value(operator, value)  # 2024-04-07 add
    if operator in op_func_mapping:
        return op_func_mapping.get(operator)(column, value)
    return column.op(operator)(value)


def _get_parse_options(cls, pss_payload):
    search = pss_payload.get('search') or pss_payload.get('query') or {}
    return {
        'str_sep': _get_parse_option(cls, search, _get_parse_option_keywords('str_sep'), '||', '||'),
        'ignore_null': _get_parse_option(cls, search, _get_parse_option_keywords('ignore_null'), True) is not False,  # 2023-12-12 add
        'like_join': 'and' if _get_parse_option(cls, search, _get_parse_option_keywords('like_join'), 'or', 'or').lower() == 'and' else 'or',  # 2023-12-23 add
        'notlike_join': 'or' if _get_parse_option(cls, search, _get_parse_option_keywords('notlike_join'), 'and', 'and').lower() == 'or' else 'and'
    }


def _get_parse_option(cls, search_payload, keys, not_contained_default, none_default=None):
    """
    Get pss_payload parsing option item
    """
    if not contains_any(search_payload, keys):
        return not_contained_default
    opt = _get_first_non_column_field_value(cls, search_payload, keys)[1]
    if opt is None:
        return none_default
    return opt


def _get_first_non_column_field_value(cls, props, fields):
    """
    Get the value of the first non-column field in the specified dictionary
    """
    for field in fields:
        if field in props and cls.get_column_by_field(field) is None:
            return field, props.get(field)
    return None, None


def _filter_pss_list(items):
    return [item for item in items if item is not None]


def _get_parse_option_keywords(keyword):
    return ['_' + keyword, keyword]


# -------------------------------------------search/like-------------------------------------------
def _parse_search_like_filters(cls, search, search_like, search_ilike, search_notlike, search_notilike):
    """
    Get like list by like_columns.
    """

    like_columns = []
    cls_like_columns_field, cls_like_columns = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('like_columns'))  # @2024-01-17 add
    if type(cls_like_columns) is not list:
        cls_like_columns = getattr(cls, 'like_columns', [])
    for col in cls_like_columns:
        if is_str(col):
            col = cls.get_column_by_field(col)
        if col is not None:
            like_columns.append(col)
    if len(like_columns) == 0:
        return [], [], [], []

    like_filters = _gen_like_columns_filters(like_columns, 'like', search_like)
    ilike_filters = _gen_like_columns_filters(like_columns, 'ilike', search_ilike)
    notlike_filters = _gen_like_columns_filters(like_columns, 'notlike', search_notlike)
    notilike_filters = _gen_like_columns_filters(like_columns, 'notilike', search_notilike)
    return like_filters, ilike_filters, notlike_filters, notilike_filters


def _get_search_like_values(cls, search, include_field=False):
    search_like_field, search_like = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('like'))
    search_ilike_field, search_ilike = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('ilike'))
    search_notlike_field, search_notlike = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('notlike'))
    search_notilike_field, search_notilike = _get_first_non_column_field_value(cls, search, _get_parse_option_keywords('notilike'))
    if include_field is True:
        return [(search_like_field, search_like), (search_ilike_field, search_ilike), (search_notlike_field, search_notlike), (search_notilike_field, search_notilike)]
    return [search_like, search_ilike, search_notlike, search_notilike]


def _gen_like_columns_filters(like_columns, like_op, like_value):
    """Generate the like filters"""
    if like_value is None or type(like_value) is not str or like_value == '':
        return []

    # if not (like_value.startswith('%') or like_value.startswith('%')):
    #     like_value = "%" + like_value + "%"
    like_value = _get_operator_value(like_op, like_value)
    filters = []
    for col in like_columns:
        # filters.append(get_col_op(col, like_op, like_value))
        filters.append(get_col_op(col, like_op, like_value))
    return filters


def _merge_search_filter_likes(pss_options, parse_option):
    filters = []
    filter_likes = pss_options.pop('filter_likes', [])
    filter_likes.extend(pss_options.pop('filter_ilikes', []))
    if len(filter_likes) > 0:
        if parse_option.get('like_join') == 'and':
            filters.append(and_(*filter_likes))
        else:
            filters.append(or_(*filter_likes))

    filter_notlikes = pss_options.pop('filter_notlikes', [])
    filter_notlikes.extend(pss_options.pop('filter_notilikes', []))
    if len(filter_notlikes) > 0:
        if parse_option.get('notlike_join') == 'or':
            filters.append(or_(*filter_notlikes))
        else:
            filters.append(and_(*filter_notlikes))
    pss_options['filter_likes'] = filters


def _get_operator_value(operator, value):
    if operator in ('like', 'ilike', 'notlike', 'notilike'):
        if not (value.startswith('%') or value.endswith('%')):
            return "%" + value + "%"
    return value


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
