from sqlalchemy import Integer, Numeric

from .. import res_status_codes

__all__ = ['BaseModelMixin']


class BaseModelMixin:
    # -------------------------------------------about model-------------------------------------------
    @classmethod
    def get_class_name(cls):
        """
        Get the name of the model class.

        Example:
            User.get_class_name() #User

        :return:
        """
        return cls.__name__

    @classmethod
    def get_columns(cls):
        """
        Get all the columns of the model class.

        Example:
            User.get_cls_columns()

        :return:
        """
        return cls.__table__.columns

    @classmethod
    def get_columns_fields(cls):
        """
        Get all the column fields.

         .. versionadded:: 1.3

        Example:
            User.get_columns_fields()

        :return:
        """
        fields = []
        for col in cls.get_columns():
            fields.append(cls.get_column_field(col))  # col.key
        return fields

    @classmethod
    def get_column_field(cls, col):
        """
        Get the field variable name of the column, default return the key of the column.
        Used to get json fields to create or update data(filter_attrs_by_columns), or convert data to json(_to_json).

        If the field name is different from the database column name
        #1 set field in info dict.(recommend)
        system_default = Column('default', Boolean, default=False, info={'field': 'system_default'})

        #2 rewrite to get the field name
        system_default = Column('default', Boolean, default=False)
        @classmethod
        def get_column_field(cls, col):
            key = col.key
            if key == 'default':
                return 'system_default'
            return key

        :param col:
        :return:
        """
        field = col.info.get('field')
        if field:
            return field
        return col.key

    @classmethod
    def get_column_by_field(cls, field):
        """
        Get the column of the specified field.

        Example:
            User.get_column_by_field('name')

        :param field:
        :return:
        """
        for col in cls.get_columns():
            if (cls.get_column_field(col)) == field:
                return col

    @classmethod
    def get_primary_column(cls):
        """
        Get the primary column of the model class.

        Example:
            User.get_primary_column()   # id column

        :return:
        """
        return find_list(cls.get_columns(), lambda c: c.primary_key is True)

    @classmethod
    def get_primary_key(cls):
        """
        Get the key of the primary column.

        Example:
            User.get_primary_key()  # 'id'

        :return:
        """
        col = cls.get_primary_column()
        if col is not None:  # must
            return col.key
        return None

    @classmethod
    def get_primary_field(cls):
        """
        Get the field of the primary column.

        Example:
            User.get_primary_field()    # 'id'

        :return:
        """
        col = cls.get_primary_column()
        if col is not None:  # must
            return cls.get_column_field(col)  # col.key
        return None

    @classmethod
    def get_unique_columns(cls):
        """
        Get the unique column list of the model class.

        Example:
            User.get_unique_columns()

        :return:
        """
        return filter_list(cls.get_columns(), lambda col: col.unique is True)

    @classmethod
    def get_relationships(cls):
        """
        Get all the relationship list of the model class.

        Example:
            User.get_relationships()

        :return:
        """
        return cls.__mapper__.relationships

    # -------------------------------------------About data-------------------------------------------
    def refresh(self):
        """
        Expire and refresh attributes on the current instance.

        .. versionadded:: 1.6.4

        Example:
            user = User.query_by({'name': 'flaskz'}, True)
            # ...
            user.refresh()

        :return:
        """
        _refresh_instance(self)  # @2023-10-17 add

    def to_dict(self, option=None):
        """
        Convert model data to dict.

        ins_to_dict(A, {
            'cascade': 3,  # 如果子项没有cascade，则使用父项-1，如果cascade不大于0，则不对象属性
            'recursion_value': '{...}'
            # 'include': ['a1'],  # 只有include中的字段才会返回，不区分值是否是对象，include的优先级>exclude
            # 'exclude': ['a2'],  # 只有exclude外的字段才会返回，不区分值是否是对象
            # 'getattr_items': lambda ins, item_cascade, option, path_keys: ins.__dict__.items(),
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

        过滤
            -不同的class会有不同的条件过滤-->过滤掉不需要的属性(create_user/password)
            -过滤条件可以是class上的属性，也可以是传递到方法中的exclude
                -如果有include--->只返回include中的属性
                -如果没有include而有exclude--->将exclude中的属性过滤掉
        # 如果属性是关系对象/列表，则



        # 单个对象很容易处理，但是 relationships不好处理
        # 不同的relationship，cascade不同
        # relation中可能有嵌套
        # 有可能两个对象里都有同一个对象
        """
        opt = {
            'getattrs': lambda ins, *args, **kwargs: ins.__class__.get_to_dict_attrs(ins, *args, **kwargs),
            'include': lambda ins, key: ins.__class__.to_dict_field_filter(key),
        }
        if option:
            opt.update(option)
        return ins_to_dict(self, opt)

    @classmethod
    def get_to_dict_attrs(cls, ins, cascade, *args):
        """to_dict attr """
        fields = [cls.get_column_field(col) for col in cls.get_columns()]
        if cascade > 0:
            for relationship in cls.get_relationships():
                lazy = relationship.lazy
                if lazy != 'dynamic' and lazy != 'noload':
                    fields.append(relationship.key)
        items = {}
        for field in fields:
            items[field] = getattr(ins, field, None)
        return items

    @classmethod
    def to_dict_field_filter(cls, field):
        """
        to_dict field filter callback.
        If return false, the field will not be returned.
        :param field:
        :return:
        """
        return True

    @classmethod
    def filter_attrs_by_columns(cls, data):
        """
        Filter out the attributes(dict) corresponding to the columns from the specified data(dict).

        :param data:
        :return:
        """
        attrs = {}
        auto_columns = getattr(cls, 'auto_columns', [])
        auto_fields = []
        for col in auto_columns:
            if is_str(col):
                auto_fields.append(col)
            else:
                auto_fields.append(cls.get_column_field(col))

        for col in cls.get_columns():
            field = cls.get_column_field(col)  # col.key
            if (field in data) and (field not in auto_fields) and (not col.info.get('auto', False)):
                col_type = col.type
                value = data.get(field)
                is_blank_str = is_str(value) and value.strip() == ""
                if col.nullable is False:
                    if not (value is None or is_blank_str):
                        attrs[field] = value
                else:
                    # @2023-05-16 add to fix DataError: (1366, "Incorrect integer value: '' for column")
                    if is_blank_str and (isinstance(col_type, Integer) or isinstance(col_type, Numeric)):
                        attrs[field] = None
                    else:
                        attrs[field] = value

        return attrs

    @classmethod
    def get_columns_json(cls, data):
        """
        Get the attributes(dict) corresponding to the column from the specified data(dict).

        .. deprecated:: 1.5 please use filter_attrs_by_columns method

        :param data:
        :return:
        """

        return cls.filter_attrs_by_columns(data)

    # -------------------------------------------add-------------------------------------------
    @classmethod
    def check_add_data(cls, data):
        """
        Check the the added json data.
        --validate the json data
        --check unique
        If the check result is not True, the adding process will be terminated and the check result will be returned to the client.

        :param data:  The data to be added
        :return: True|Error Message
        """
        if not is_dict(data):
            if data:
                return data
            return res_status_codes.bad_request
        return cls._check_unique(data)

    @classmethod
    def add_db(cls, data):
        """
        Add data to the db.

        Example:
            ins = User.add_db({"name": "taozh", "email": "taozh@focus-ui.com"})

        :param data:
        :return:
        """

        instance = create_instance(cls, data)
        with _db_session(False, True) as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)  # If not, the value in the instance is not consistent with the database, and the query will be send until accessing the attributes.

        return instance

    @classmethod
    def bulk_add(cls, items, with_relationship=False):
        """
        Perform a bulk add of the given list of mapping dictionaries.(atomic)

        sa version upgrade: https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html
        :param items:
        :param with_relationship:
        :return:
        """
        if len(items) == 0:
            return
        if with_relationship is True:
            with db_session() as session:
                ins_list = []
                for data_item in items:
                    ins_list.append(create_instance(cls, data_item))
                session.add_all(ins_list)
        else:
            with db_session() as session:
                session.bulk_insert_mappings(cls, items)

    # -------------------------------------------update-------------------------------------------
    @classmethod
    def check_update_data(cls, data):
        """
        Check the the updated json data.
        --validate the json data
        --check exist
        --check unique
        If the check result is not True, the update process will be terminated and the check result will be returned to the client.

        :param data: The updated json data
        :return:
        """
        if not is_dict(data):
            if data:
                return data
            return res_status_codes.bad_request

        exist = cls._check_exist(data)
        if exist is not True:
            return exist
        return cls._check_unique(data)

    @classmethod
    def update_db(cls, data):
        """
        Update the data to the db. The primary key value must be in data.
        Only the fields in data will be updated.

        Example:
            ins = User.update_db({"id": 1, "email": "taozh@focus-ui.com"})

        :param data:
        :return:
        """
        pk_value = cls._get_pk_value(data)
        if pk_value is None:  # pk value does not exist
            return res_status_codes.db_data_not_found

        with _db_session(False, True) as session:
            instance = _session_get(session, cls, pk_value)  # session.query(cls).get(pk_value)  # Scenarios for extending BaseModelMixin instead of ModelMixin
            if instance is None:  # Object does not exist
                return res_status_codes.db_data_not_found
            cls._update_ins(instance, data)  # @2022-12-01 change to ensure the updated instance and the setattr action in the same session
            session.commit()
            session.refresh(instance)  # If not, the value in the instance is not consistent with the database, and the query will be send until accessing the attributes.
        return instance

    @classmethod
    def bulk_update(cls, items, with_relationship=False):
        """
        Perform a bulk update of the given list of mapping dictionaries.(atomic)

        sa version upgrade: https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html
        :param items:
        :param with_relationship:
        :return:
        """
        if len(items) == 0:
            return

        if with_relationship is True:
            with db_session() as session:
                for data in items:
                    pk_value = cls._get_pk_value(data)
                    if pk_value is not None:
                        # cls._update_ins(session.query(cls).get(pk_value), data)  # @2022-12-01 change to ensure the updated instance and the setattr action in the same session
                        cls._update_ins(_session_get(session, cls, pk_value), data)  # @2022-12-01 change to ensure the updated instance and the setattr action in the same session
        else:
            with db_session() as session:
                session.bulk_update_mappings(cls, items)

    @classmethod
    def _update_ins(cls, instance, data):
        if instance:
            for field, value in cls.filter_attrs_by_columns(data).items():  # Only the fields in json will be updated
                setattr(instance, field, value)  # @2023-05-11, data.get(field)-->ins_attrs.get(field)
            relationships = create_relationships(cls, data)
            for field in relationships:
                setattr(instance, field, relationships[field])
        return instance

    # -------------------------------------------delete-------------------------------------------
    @classmethod
    def check_delete_data(cls, pk_value):
        """
        Check the the deleted data.
        --validate the deleted data
        --check exist
        If the check result is not True, the delete process will be terminated and the check result will be returned to the client.

        :param pk_value:
        :return:
        """
        if pk_value is None:
            return res_status_codes.db_data_not_found

        pk = cls.get_primary_field()
        data = {pk: pk_value}
        return cls._check_exist(data)

    @classmethod
    def delete_db(cls, pk_value):
        """
        Delete the specified data with the specified primary key value.

        Example:
            ins = User.delete_db(1)   # pk
            ins = User.delete_db({'id': 1})   # dict

        :param pk_value:
        :return:
        """
        if pk_value is None:  # Object does not exist
            return res_status_codes.db_data_not_found
        with db_session() as session:  # @2022-12-01 change to ensure the deleted instance and the delete action in the same session
            if is_dict(pk_value):  # @2023-03-27 add
                instance = session.query(cls).filter_by(**pk_value).limit(1).first()
            else:
                # instance = session.query(cls).get(pk_value)
                instance = _session_get(session, cls, pk_value)
            if instance is None:  # Object does not exist
                return res_status_codes.db_data_not_found
            session.delete(instance)
        return instance

    @classmethod
    def bulk_delete(cls, items):
        """
        Perform a bulk delete of the given list of mapping dictionaries.(not atomic)

        .. versionupdated:: 1.0

        Example:
            User.bulk_delete([1,2,3])   # pk list
            User.bulk_delete([{'id': 1}, {'id': 2}, {'id': 3}]) # dict list

        :param items:
        :return: the deleted count
        """
        if len(items) == 0:
            return
        pk = cls.get_primary_field()
        count = 0
        with db_session() as session:
            pk_list = []
            for item in items:
                if is_dict(item):
                    # instance = session.query(cls).filter_by(**item).limit(1).first()
                    # if instance:
                    #     pk_list.append(getattr(instance, pk))
                    for instance in session.query(cls).filter_by(**item):  # @2023-03-27 first to all, ex)delete all items with same name
                        pk_list.append(getattr(instance, pk))
                else:
                    pk_list.append(item)
            # @2022-11-03: Use 'where' and 'in' to rewrite bulk delete to avoid partial delete scenarios
            if len(pk_list) > 0:
                count = session.query(cls).filter(getattr(cls, pk).in_(pk_list)).delete()
        return count

    @classmethod
    def clear_db(cls):
        """
        Clear all the data.

        .. versionadded:: 1.6

        Example:
            SysActionLog.clear_db()

        :return: the deleted count
        """
        with db_session() as session:
            return session.query(cls).delete()

    # -------------------------------------------query-------------------------------------------

    @classmethod
    def query(cls):
        """
        Return a 'Query' object corresponding to this class.

        Example:
            query = TemplateModel.query()
            print(query.all())

        :return:
        """
        with db_session(do_commit=False) as session:
            return session.query(cls)

    @classmethod
    def get_query_default_order(cls):
        """
        Get the default order of the query.(column key, not field)

        get_primary_key-->get_primary_column to fix
        sqlalchemy.exc.CompileError: Can't resolve label reference for ORDER BY / GROUP BY / DISTINCT etc.
            Textual SQL expression 'id' should be explicitly declared as text('id')
        :return:
        """
        return cls.get_primary_column()

    @classmethod
    def query_by_unique_key(cls, data):
        """
        Query data by the unique values.
        --If exist,returns the instance.
        --Otherwise,returns None

        Example:
            ins = User.query_by_unique_key(data)

        :param data:
        :return:
        """
        cols = cls.get_unique_columns()
        if len(cols) == 0:
            return None

        ors = []
        for col in cols:
            field = cls.get_column_field(col)  # col.key
            value = data.get(field)
            if value is not None:  # maybe 0
                ors.append(get_col_op(col, '==', value))  # @2023-08-16, text-->op

        if len(ors) == 0:
            return None

        with db_session(do_commit=False) as session:
            query = session.query(cls)
            query = append_query_filter(query, ors, 'or')
            instance = query.first()
        return instance

    @classmethod
    def query_by_pk(cls, pk_value):
        """
        Query by pk value.

        Example:
            ins = User.query_by_pk(1)

        :param pk_value:
        :return:
        """
        with db_session(do_commit=False) as session:
            # instance = session.query(cls).get(pk_value)
            instance = _session_get(session, cls, pk_value)
        return instance

    @classmethod
    def query_by(cls, by_dict, return_first=False):
        """
        Query by dict object.
        -If first is not True, return the list result of the query.
        -If first is True, return the first row object or None.

        Example:
            ins_list = User.query_by({'name': 'flaskz'})   # list
            ins = User.query_by({'name': 'flaskz'}, True) # first row

        """
        with db_session(do_commit=False) as session:
            if return_first is True:
                result = session.query(cls).filter_by(**by_dict).limit(1).first()
            else:
                result = session.query(cls).filter_by(**by_dict).all()
        return result

    @classmethod
    def query_all(cls):
        """
        Query all the data of the model class.

        Example:
            ins_list = User.query_all()

        :return:
        """
        query_order = cls.get_query_default_order()
        with db_session(do_commit=False) as session:
            query = session.query(cls)
            if query_order is not None:
                query = query.order_by(query_order)
            result = query.all()
        return result

    @classmethod
    def query_pss(cls, pss_option):
        """
        Query data by search, pagination and sort condition.
        Please use flaskz.utils.get_pss to parse option first.
        pss = page+search+sort

        Example:
            result = TemplateModel.query_pss(get_pss(   # use flaskz.utils.get_pss to format condition
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
                    # "sort":[                          # ORDER BY templates.name ASC, templates.age DESC
                    #     {"field": "name", "order": "asc"},
                    #     {field": "age", "order": "desc"}
                    # ],
                    "page": {                           # LIMIT ? OFFSET ? (20, 0)
                        "offset": 0,
                        "size": 20
                    }
                }))

        # sql
        SELECT templates.id AS templates_id, templates.name AS templates_name, templates.age AS templates_age, templates.email AS templates_email,
                templates.country AS templates_country, templates.grade AS templates_grade, templates.description AS templates_description,
                templates.created_at AS templates_created_at, templates.updated_at AS templates_updated_at
        FROM templates
        WHERE
            (name like '%t%' OR description like '%t%')
            AND (grade>1 AND grade<5 AND age>1 AND age<20 AND email='taozh@focus-ui.com')
            AND (country='America' OR country='Canada')
        ORDER BY templates.name ASC
        LIMIT ? OFFSET ? (20, 0)

        :param pss_option:
        :return:
        """
        return cls._query_pss(pss_option)

    @classmethod
    def count(cls, search=None):
        """
        Return the count of the specified search, if search option is None, return the count of all data.

        .. versionadded:: 1.6

        Example:
            SysActionLog.count()
            SysActionLog.count(get_pss(   # use flaskz.utils.get_pss to format condition
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
                    }
                }))
        :param search: the search option
        :return: the count number
        """
        return cls._query_pss(search, True)

    @classmethod
    def _query_pss(cls, pss_option, return_count=False):
        pss_option = pss_option or {}
        filter_likes = pss_option.get('filter_likes', [])
        filter_ands = pss_option.get('filter_ands', [])
        filter_ors = pss_option.get('filter_ors', [])

        group = pss_option.get('group', [])

        offset = max(get_dict_value_by_type(pss_option, 'offset', int, 0), 0)  # @2023-01-09 update, add type check
        limit = max(get_dict_value_by_type(pss_option, 'limit', int, 0), 0)
        # distinct = pss_option.get('distinct', [])

        orders = pss_option.get('order')
        if orders is None:
            orders = []
        elif not is_list(orders):  # asc/desc
            orders = [orders]

        if len(orders) == 0:  # @2023-05-04 fix
            orders = [cls.get_query_default_order()]  # default order
        orders = [item for item in orders if item is not None]

        with db_session(do_commit=False) as session:
            query = session.query(cls)

            query = append_query_filter(query, filter_likes, 'or')
            query = append_query_filter(query, filter_ands, 'and')
            query = append_query_filter(query, filter_ors, 'or')
            # if len(filter_likes) > 0:
            #     query = query.filter(text('(' + (' OR '.join(filter_likes)) + ')'))
            # if len(filter_ands) > 0:
            #     query = query.filter(text('(' + (' AND '.join(filter_ands)) + ')'))
            # if len(filter_ors) > 0:
            #     query = query.filter(text('(' + (' OR '.join(filter_ors)) + ')'))

            # if len(distinct) > 0:
            #     query.distinct(*distinct)

            if len(group) > 0:  # @2023-06-07 add
                query = query.group_by(*group)

            count = query.count()

            if return_count is True:
                return count

            if count > 0 and offset < count:
                # for order in orders:
                #     if order is not None:
                #         query = query.order_by(order)
                if len(orders) > 0:
                    query = query.order_by(*orders)

                query = query.offset(offset)
                if limit > 0:
                    query = query.limit(limit)
                items = query.all()
            else:
                items = []
        return {
            'count': count,
            'data': items
        }

    # -------------------------------------------check-------------------------------------------
    @classmethod
    def _get_pk_value(cls, data):
        """
        Get the primary key value from the json data.

        :param data:
        :return:
        """
        pk = cls.get_primary_field()
        if pk:
            return data.get(pk)

    @classmethod
    def _check_exist(cls, data):
        """
        Check whether the data exists.
        Return True if exists, else return not found code.

        :param data:
        :return:
        """
        pk_value = cls._get_pk_value(data)
        if pk_value is not None and cls.query_by_pk(pk_value):
            return True
        return res_status_codes.db_data_not_found  # used to return to the client

    @classmethod
    def _check_unique(cls, data):
        """
        Check whether the data meets uniqueness constraints.
        If meets, returns True, otherwise returns exist code.
        """
        result = cls.query_by_unique_key(data)

        if result is None:
            return True

        pk = cls.get_primary_field()
        pk_value = cls._get_pk_value(data)
        if pk_value is not None and pk_value == getattr(result, pk):
            return True
        return res_status_codes.db_data_already_exist  # used to return to the client

    def __repr__(self):
        cls = self.__class__
        attrs = []
        for col in cls.get_columns():
            field = cls.get_column_field(col)
            attrs.append(field + '=' + str(getattr(self, field, None)))
        return cls.get_class_name() + '(' + (', '.join(attrs)) + ')'

    # -------------------------------------------new-------------------------------------------


# must
from ..utils._cls import ins_to_dict
from ..utils._common import find_list, filter_list, is_str, is_dict, is_list, get_dict_value_by_type
from ._util import create_instance, create_relationships, db_session, append_query_filter, _db_session, _session_get, _refresh_instance
from ._query_util import get_col_op
