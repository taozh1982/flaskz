from contextlib import contextmanager

from flask import g

from . import DBSession
from ._model import ModelMixin
from ..utils import get_g_cache, set_g_cache

__all__ = ['create_instance', 'create_relationships',
           'query_multiple_model',
           'append_debug_queries', 'get_debug_queries',
           'get_db_session', 'db_session', 'close_db_session',
           'model_to_dict']


def create_instance(model_cls, data, create_relationship=True):
    """
    Create an instance of the specified model class with the data
    :param model_cls: The specified model class.
    :param data: The data used to create instance.
    :param create_relationship: If true, the relationships will be created.
    :return:
    """
    if not isinstance(data, dict):
        return None

    col_value_dict = model_cls.get_columns_json(data)
    instance = model_cls(**col_value_dict)

    if create_relationship is True:
        relationships = create_relationships(model_cls, data)
        for key in relationships:
            setattr(instance, key, relationships[key])
    return instance


def create_relationships(model_cls, data):
    """
    Create the relationship dict of the specified model class with the data
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


def query_multiple_model(*cls_list):
    """
    Query all the data of the multiple specified model class.
    :param cls_list:
    :return:If failed, returns the failed tuple, otherwise, returns the the data list.
    """
    result = []
    for cls in cls_list:
        r = cls.query_all()

        if type(r) is tuple:  # ModelMixin
            if r[0] is not True:  # error
                return r
            else:
                result.append(r[1])
        else:
            result.append(r)
    return result


def append_debug_queries(query):
    debug_queries = getattr(g, 'z_debug_queries', None)
    if debug_queries is None:
        g.z_debug_queries = debug_queries = []
    debug_queries.append(query)


def get_debug_queries():
    return getattr(g, 'z_debug_queries', [])


def get_db_session():
    """
    Get the db session from g.
    If not exist, create a session and return.
    :return:
    """
    session = get_g_cache('_flaskz_db_session')
    if session is None:
        session = DBSession()
        set_g_cache('_flaskz_db_session', session)

    return session


def close_db_session():
    """
    Close the session in the g
    :return:
    """
    session = get_g_cache('_flaskz_db_session')
    if session is not None:
        session.close()


@contextmanager
def db_session(do_commit=True):
    """
    Database session context manager.

    instance = create_instance(cls, json_data)
    with db_session() as session:
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


def model_to_dict(ins, option=None):
    """
    Convert model data to json dict

    :param ins:
    :param option:
    :return:
    """
    if isinstance(ins, list):
        data_list = []
        for item in ins:
            if isinstance(item, ModelMixin):
                data_list.append(item.to_dict(option))
            else:
                data_list.append(item)
        return data_list
    elif isinstance(ins, ModelMixin):
        return ins.to_dict(option)
    else:
        return ins
