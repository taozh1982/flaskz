from contextlib import contextmanager

from flask import g

from . import DBSession
from ._base import BaseModelMixin
from ..utils import get_g_cache, set_g_cache

__all__ = ['create_instance', 'create_relationships',
           'query_all_models', 'query_multiple_model',
           'append_debug_queries', 'get_debug_queries',
           'get_db_session', 'db_session', 'close_db_session',
           'model_to_dict',
           'is_model_mixin_instance'
           ]


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


def append_debug_queries(query):
    if _has_g_context():  # @2022-07-26 add,
        debug_queries = getattr(g, 'z_debug_queries', None)
        if debug_queries is None:
            g.z_debug_queries = debug_queries = []
        debug_queries.append(query)


def get_debug_queries():
    if _has_g_context():  # @2022-07-26 add,
        return getattr(g, 'z_debug_queries', [])
    return []


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
    if _has_g_context():  # @2022-07-26 add, make sure work without flask request
        session = get_g_cache('_flaskz_db_session')
        if session is None:
            session = DBSession()
            setattr(session, '_flaskz_db_session', True)
            set_g_cache('_flaskz_db_session', session)
    else:
        session = DBSession()
    return session


def close_db_session():
    """
    Close the session in the g.

    :return:
    """
    if _has_g_context():  # @2022-07-26 add
        session = get_g_cache('_flaskz_db_session')
        if session is not None:
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
    if getattr(session, '_flaskz_db_session', None) is not True:  # @2023-05-06: add, close non-cached session
        session.close()


def model_to_dict(ins, option=None):
    """
    Convert model data to dict.

    Example:
        result = Role.update(request_json)
        res_data = model_to_dict(result[1], {'cascade': 1})

    :param ins:
    :param option:
    :return:
    """
    if isinstance(ins, list):
        data_list = []
        for item in ins:
            if is_model_mixin_instance(item):  # @2022-11-28: change, ModelMixin --> BaseModelMixin
                data_list.append(item.to_dict(option))
            else:
                data_list.append(item)
        return data_list
    elif is_model_mixin_instance(ins):
        return ins.to_dict(option)
    else:
        return ins


def is_model_mixin_instance(obj):
    """
    Check if the object is an instance of the BaseModelMixin.

    :param obj:
    :return:
    """
    return isinstance(obj, BaseModelMixin)


def _has_g_context():
    # if has_request_context():  # If there is request context, g must exist
    #     return True
    if not g:  # @2022-11-28: change, (not g) != (g is None)
        return False
    return True
    # return has_request_context() or g is not None
