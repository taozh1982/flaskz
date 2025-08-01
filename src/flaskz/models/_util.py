from contextlib import contextmanager

from flask import g
from sqlalchemy import text, or_, and_, inspect
from sqlalchemy.sql.elements import BinaryExpression  # @2024-01-04 update, BinaryExpression not in sqlalchemy.__init__.py when sqlalchemy<2.0.0

from . import DBSession
from ._base import BaseModelMixin
from ..utils import get_g_cache, set_g_cache, remove_g_cache, get_dict_mapping, get_ins_mapping

__all__ = ['create_instance', 'create_relationships',
           'query_all_models', 'query_multiple_model', 'query_from_g_cache',
           'append_debug_queries', 'get_debug_queries', 'append_query_filter',
           'get_db_session', 'db_session', 'close_db_session',
           'model_to_dict', 'refresh_instance',
           'is_model_mixin_instance']


def create_instance(model_cls, data, create_relationship=True):
    """
    Create an instance of the specified model class with the data.

    Example:
        create_instance(User, {"name": "taozh", "email": "taozh@focus-ui.com"})

    :param model_cls: The specified model class.
    :param data: The data used to create instance.
    :param create_relationship: If true, the relationships will be created.
    :return:
    """
    if not isinstance(data, dict):
        return None

    col_value_dict = model_cls.filter_attrs_by_columns(data)
    instance = model_cls(**col_value_dict)

    if create_relationship is True:
        relationships = create_relationships(model_cls, data)
        for key in relationships:
            setattr(instance, key, relationships[key])
    return instance


def create_relationships(model_cls, data):
    """
    Create the relationship dict of the specified model class with the data.

    :param model_cls:
    :param data:
    :return:
    """
    relationships = model_cls.get_relationships()
    relationship_map = {}
    for key in relationships.keys():
        relationship_cls = relationships[key].mapper.class_
        relationship_kwargs = data.get(key)
        if isinstance(relationship_kwargs, list):  # 1:n
            relationship = []
            for item in relationship_kwargs:
                r_ins = create_instance(relationship_cls, item)
                if r_ins is not None:
                    relationship.append(r_ins)
        else:
            relationship = create_instance(relationship_cls, relationship_kwargs)  # 1:1

        if relationship is not None:
            relationship_map[key] = relationship

    return relationship_map


def query_all_models(*models):
    """
    Query all the data of the specified model(ModelMixin) list.

    .. versionadded:: 1.5

    Example:
        result = query_all_models(User, Role)

    :param models:
    :return:
    """
    result = []
    for model in models:
        r = model.query_all()

        if type(r) is tuple:  # ModelMixin
            if r[0] is not True:  # error
                return r
            else:
                result.append(r[1])
        else:
            result.append(r)
    return result


def query_multiple_model(*cls_list):
    """
    Query all the data of the multiple specified model(ModelMixin) class.

    Example:
        result = query_multiple_model(User, Role)

    :param cls_list:
    :return:If failed, returns the failed tuple, otherwise, returns the the data list.
    """

    return query_all_models(*cls_list)


def query_from_g_cache(model_class, by_value, attr=None, to_dict=True, mapping_key=None, cache_key=None):
    """
    Query data from g(flask), if data not exist, query first and cache.

    .. versionadded:: 1.8.0

    Example:
        query_from_g_cache(User, 1)  # return 'dict' of User properties with id=1
        query_from_g_cache(User, 1, 'username')  # return 'username' property of User with id=1
        query_from_g_cache(User, 'admin', mapping_key='username')  # use 'username' as key of the cached dict
        query_from_g_cache(User, 1, to_dict=False)  # id=1(ins) # cache 'instance'
        query_from_g_cache(User, False)  # return 'all' users

    :param model_class: the model class to query and cache, ex)User
    :param by_value: the value to query, if False return all items ex) 1/'admin'
    :param attr: the attribute of the data to return, ex)'username'/'email'
    :param to_dict: cache data as dict or not, ex) True/False
    :param mapping_key: the key used to create data mapping, if None, use the primary filed of the model_class, ex)'id'
    :param cache_key: the key used to cache data, if None use 'flaskz_' + class_name + '_model_cached_items'
    :return:
    """
    if by_value is None:
        return None
    class_name = model_class.get_class_name()
    if cache_key is None:
        cache_key = 'flaskz_' + class_name + '_model_cached_items'
    mapping = get_g_cache(cache_key)

    if mapping is None:
        if mapping_key is None:  # if key is None, use primary_field of the model_class
            mapping_key = model_class.get_primary_field()
        success, data = model_class.query_all()
        if success:
            if to_dict is True or type(to_dict) is dict:
                _to_dict_option = to_dict if type(to_dict) is dict else None
                mapping = get_dict_mapping(model_to_dict(data, _to_dict_option), mapping_key)
            else:
                mapping = get_ins_mapping(data, mapping_key)
            set_g_cache(cache_key, mapping)
    if mapping:
        if by_value is False:  # if pk_value is False, return all items
            return list(mapping.values())
        item = mapping.get(by_value)
        if item and attr is not None:
            if to_dict is True:
                return item.get(attr)
            else:
                return getattr(item, attr, None)
        return item


def append_debug_queries(query):
    if _has_flask_g_context():  # @2022-07-26 add,
        debug_queries = getattr(g, 'z_debug_queries', None)
        if debug_queries is None:
            g.z_debug_queries = debug_queries = []
        debug_queries.append(query)


def get_debug_queries():
    if _has_flask_g_context():  # @2022-07-26 add,
        return getattr(g, 'z_debug_queries', [])
    return []


def _append_pss_query_filters(query, pss_option):
    query = append_query_filter(query, pss_option.get('filter_likes', []), 'and')
    # query = append_query_filter(query, pss_option.get('filter_notlikes', []), 'and')
    query = append_query_filter(query, pss_option.get('filter_ands', []), 'and')
    query = append_query_filter(query, pss_option.get('filter_ors', []), 'or')

    # query = append_query_filter(query, pss_option.get('filters', []), 'and')  # for search
    return query


def append_query_filter(query, filters, joined=None):  # @2023-06-21 add
    """
    Append filters to the query
    :param query:
    :param filters:
    :param joined:
    :return:
    """
    if len(filters) == 0:
        return query

    text_items = []
    binary_expression_items = []
    clause_items = []
    for item in filters:
        item_type = type(item)
        if item_type is str:
            text_items.append(item)
        elif item_type is BinaryExpression:
            binary_expression_items.append(item)
        else:
            clause_items.append(item)  # and(ed) / or(ed)

    if len(clause_items) > 0:
        query = query.filter(*clause_items)

    joined = joined.lower()
    if joined == 'or':
        joined_text = ' OR '
        joined_func = or_
    elif joined == 'and':
        joined_text = ' AND '
        joined_func = and_
    else:
        return query

    if len(text_items) > 0:
        query = query.filter(text('(' + (joined_text.join(text_items)) + ')'))
    if len(binary_expression_items) > 0:
        query = query.filter(joined_func(*binary_expression_items))

    return query


def get_db_session():
    """
    Get the db session from g(flask)/ Create a db session(without request).
    If not exist, create a session and return.

    Example:
        session = get_db_session()
        session.query(User).all()
        session.close()             # close session

    :return:
    """
    # @2022-07-26 add `_has_g_context` condition to make sure work without flask request,
    # @2024-02-02 add `reusable_in_flask_g` condition to disable cache
    if getattr(DBSession, 'reusable_in_flask_g', None) is not False and _has_flask_g_context():
        session = get_g_cache('_flaskz_db_session')
        if session is None:
            session = DBSession()
            set_g_cache('_flaskz_db_session', session)
    else:
        session = DBSession()
        setattr(session, '_temporary', True)  # @2022-08-22 add '_temporary' attr
    return session


def close_db_session():
    """
    Close the cached session.

    :return:
    """
    if _has_flask_g_context():  # @2022-07-26 add
        session = get_g_cache('_flaskz_db_session')
        if session is not None:
            remove_g_cache('_flaskz_db_session')
            session.close()


def _close_temporary_session(session):
    """
    @2023-05-06: add, close temporary(non-cached) session
    :param session:
    :return:
    """
    if getattr(session, '_temporary', None) is True:
        session.close()


@contextmanager
def db_session(do_commit=True):
    """
    Database session context manager.

    Example:
        with db_session() as session:
            instance = create_instance(cls, json_data)
            session.add(instance)

    :param do_commit: If false, session will not commit,generally used for query operations
    :return:
    """
    session = get_db_session()
    try:
        yield session
        if do_commit is not False:
            session.commit()
    except Exception as e:
        if do_commit is not False:
            session.rollback()
        raise e
    _close_temporary_session(session)


@contextmanager
def _db_session(do_commit, do_rollback):
    """
    # @2023-08-21: add, for internal use
    """
    session = get_db_session()
    try:
        yield session
        if do_commit is True:
            session.commit()
    except Exception as e:
        if do_rollback is True:
            session.rollback()
        raise e
    _close_temporary_session(session)


def model_to_dict(ins, option=None):
    """
    Convert model data to dict.

    Example:
        result = Role.update(request_json)
        res_data = model_to_dict(result[1], {
            'cascade': 1
            # 'filter': lambda ins: ins.type == 'local'
        })

    :param ins:
    :param option:
    :return:
    """

    if isinstance(ins, list):
        data_list = []
        ins_filter = None
        if type(option) is dict:
            ins_filter = option.get('filter')
        if not callable(ins_filter):
            ins_filter = None
        for item in ins:
            if ins_filter and ins_filter(item) is not True:  # 2023-09-19: add
                continue
            if is_model_mixin_instance(item):  # @2022-11-28: change, ModelMixin --> BaseModelMixin
                data_list.append(item.to_dict(option))
            else:
                data_list.append(item)
        return data_list
    elif is_model_mixin_instance(ins):
        return ins.to_dict(option)
    else:
        return ins


def refresh_instance(ins):
    """
    Expire and refresh attributes on the given instance/list

    .. versionadded:: 1.6.4

    Example:
        user = User.query_by({'name': 'flaskz'}, True)
        # ...
        refresh_instance(user)

        user_list = User.query_by({'name': 'flaskz'})
        # ...
        refresh_instance(user_list)

    :param ins:
    :return:
    """
    if ins is None:
        return
    if not isinstance(ins, list):
        ins_list = [ins]
    else:
        ins_list = ins
    for item in ins_list:
        _refresh_instance(item)


def _refresh_instance(ins):  # @2023-10-17 add
    if not is_model_mixin_instance(ins):
        return
    ins_inspect = inspect(ins)
    ins_session = ins_inspect.session
    if ins_session and ins_session.is_active is True:
        ins_session.refresh(ins)


def is_model_mixin_instance(obj):
    """
    Check if the object is an instance of the BaseModelMixin.

    :param obj:
    :return:
    """
    return isinstance(obj, BaseModelMixin)


def _has_flask_g_context():
    # if has_request_context():  # If there is request context, g must exist
    #     return True
    if not g:  # @2022-11-28: change, (not g) != (g is None)
        return False
    return True
    # return has_request_context() or g is not None


# _sa_version = parse_version(sqlalchemy.__version__)
# if _sa_version[0] > 2 or _sa_version[0] > 1 and _sa_version[1] >= 4:
#     def _session_get(session, cls, ident):
#         """Return an instance based on the given primary key identifier, or None if not found."""
#         return session.get(cls, ident)
# else:
#     def _session_get(session, cls, ident):
#         """Return an instance based on the given primary key identifier, or None if not found."""
#         return session.query(cls).get(ident)

def _session_get(session, cls, ident):  # @2023-12-08 update sqlalchemy and replace session.query(cls).get(ident) --> session.get(cls, ident)
    """Return an instance based on the given primary key identifier, or None if not found."""

    return session.get(cls, ident)
