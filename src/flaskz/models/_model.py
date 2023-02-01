from sqlalchemy.exc import IntegrityError

from ._base import BaseModelMixin
from ._util import is_model_mixin_instance
from .. import res_status_codes
from ..log import flaskz_logger
from ..utils import is_dict

__all__ = ['ModelMixin']


class ModelMixin(BaseModelMixin):
    # -------------------------------------------add-------------------------------------------
    @classmethod
    def get_add_data(cls, data):
        """
        Return the added json data. By default, return the json data of the client
        Rewrite to customize the added data

        :param data: The data to be added
        :return:
        """
        return data

    @classmethod
    def before_add(cls, data):
        """
        The callback before adding data.
        If the return value is not True, the adding process will be terminated and the result will be returned to the client.
        :param data: The data to be added
        :return: True|Error Message
        """
        return True

    @classmethod
    def after_add(cls, data, instance, before_result):
        """
        The callback after adding data.
        If an exception occurs in after_add, the added data will not be rolled back.

        :param data: The data to be added
        :param instance: The result model instance, None if add fails.
        :param before_result: The result of the before_add callback
        :return:
        """
        pass

    @classmethod
    def add(cls, data):
        """
         Add the data to the db.
         Returns a tuple.
           --the first value represents whether the add operation was successful, True/False.
           --the second value represent the result of the add operation, reason/instance.

        :param data:
        :return:
        """
        instance = None
        try:
            data = cls.get_add_data(data)
            check_result = cls.check_add_data(data)
            if check_result is not True:  # ex)db_data_already_exist
                return False, check_result

            before_result = cls.before_add(data)
            try:
                if before_result is True:
                    instance = cls.add_db(data)
            finally:
                cls.after_add(data, instance, before_result)  # after_add execute regardless of whether the addition is successful
        except Exception as e:
            flaskz_logger.exception(e)
            return False, res_status_codes.db_add_err

        return _op_result(before_result, instance)

    # -------------------------------------------update-------------------------------------------
    @classmethod
    def get_update_data(cls, data):
        """
        Return the updated json data. By default, return the json data of the client
        Rewrite to customize the updated data

        :param data: The updated json data
        :return:
        """
        return data

    @classmethod
    def before_update(cls, data):
        """
        The callback before updating data.
        If the return value is not True, the update process will be terminated and the result will be returned to the client.

        :param data:
        :return:
        """
        return True

    @classmethod
    def after_update(cls, data, instance, before_result):
        """
        The callback after updating data.
        If an exception occurs in after_update, the updated data will not be rolled back.

        :param data:
        :param instance:
        :param before_result:
        :return:
        """
        pass

    @classmethod
    def update(cls, data):
        """
        Update the data to the db.
        Returns a tuple.
           --the first value represents whether the update operation was successful, True/False.
           --the second value represent the result of the update operation, reason/instance.

        :param data:
        :return:
        """
        instance = None
        try:
            data = cls.get_update_data(data)
            check_result = cls.check_update_data(data)
            if check_result is not True:  # ex)db_data_not_found / db_data_already_exist
                return False, check_result

            before_result = cls.before_update(data)
            try:
                if before_result is True:
                    instance = cls.update_db(data)
            finally:
                cls.after_update(data, instance, before_result)
        except Exception as e:
            flaskz_logger.exception(e)
            return False, res_status_codes.db_update_err

        return _op_result(before_result, instance)

    # -------------------------------------------delete-------------------------------------------
    @classmethod
    def get_delete_data(cls, pk_value):
        """
        Return the primary key of the data to be deleted. By default, return the primary key of the client data
        Rewrite to customize the deleted data

        :param pk_value: The primary key of the data to be deleted
        :return:
        """
        return pk_value

    @classmethod
    def before_delete(cls, pk_value):
        """
        The callback before deleting data.
        If the return value is not True, the delete process will be terminated and the result will be returned to the client.

        :param pk_value:
        :return:
        """
        return True

    @classmethod
    def after_delete(cls, pk_value, instance, before_result):
        """
        The callback after deleting data.
        If an exception occurs in after_delete, the data will still be deleted.

        :param pk_value:
        :param instance:
        :param before_result:
        :return:
        """
        pass

    @classmethod
    def delete(cls, pk_value):
        """
        Delete the data from the db.
        Returns a tuple.
           --the first value represents whether the delete operation was successful, True/False.
           --the second value represent the result of the delete operation, reason/instance.

        :param pk_value:
        :return:
        """
        if is_dict(pk_value):  # {id:10}
            pk_value = cls._get_pk_value(pk_value)

        instance = None
        try:
            pk_value = cls.get_delete_data(pk_value)
            check_result = cls.check_delete_data(pk_value)
            if check_result is not True:  # ex)db_data_not_found
                return False, check_result

            before_result = cls.before_delete(pk_value)
            try:
                if before_result is True:
                    instance = cls.delete_db(pk_value)
            finally:
                cls.after_delete(pk_value, instance, before_result)
        except IntegrityError as e:
            flaskz_logger.exception(e)
            return False, res_status_codes.db_data_in_use
        except Exception as e:
            flaskz_logger.exception(e)
            return False, res_status_codes.db_delete_err

        return _op_result(before_result, instance)

    # -------------------------------------------query-------------------------------------------
    @classmethod
    def query_all(cls):
        """
        Override the base query_all method and return success flag
        Used in router to return query data
        :return:
        """
        try:
            return True, super().query_all()
        except Exception as e:
            flaskz_logger.exception(e)
            return False, res_status_codes.db_query_err

    @classmethod
    def query_pss(cls, pss_option):
        """
        Override the base query_pss method and return success flag
        Used in router to return query data
        :param pss_option:
        :return:
        """
        try:
            return True, super().query_pss(pss_option)
        except Exception as e:
            flaskz_logger.exception(e)
            return False, res_status_codes.db_query_err


def _op_result(before_result, instance):
    if before_result is not True:
        return False, before_result
    if not is_model_mixin_instance(instance):
        return False, instance
    return True, instance
