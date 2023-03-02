import json

from flask import request
from flaskz import res_status_codes

from ..log import flaskz_logger, get_log_data
from ..models import model_to_dict, query_multiple_model, ModelMixin
from ..utils import get_list, is_dict, create_response, get_pss


def init_model_rest_blueprint(model_cls, api_blueprint, url_prefix, module, routers=None, to_json_option=None, multiple_option=None):
    """
    Append rest api route to the api blueprint for the specified model class.
    :param to_json_option: The option used to return json, fields/cascade. ex){'cascade': 1}
    :param module: The module name,ex) role/menu
    :param url_prefix: Api url path
    :param api_blueprint:
    :param model_cls: The specified model class.
    :param routers: The api router list, ex)['query', 'query_pss', 'add', 'update', 'delete']
    :param multiple_option:
    :return:
    """
    if to_json_option is None:
        to_json_option = {}

    # from ..sys_mgmt import log_operation

    # permission_required_ = current_app.model_rest_manager._permission_required
    # print(permission_required_)

    class_name = model_cls.get_class_name()
    routers = get_list(routers, ['query', 'query_pss', 'query_multiple', 'add', 'update', 'upsert', 'delete'])

    if 'add' in routers:
        @api_blueprint.route(url_prefix + '/', methods=['POST'])
        @rest_permission_required(module, 'add')
        @gen_route_method('add', url_prefix)
        def add():
            """
            add model data
            :return:
            """
            request_json = request.json
            req_log_data = json.dumps(request_json)

            success, data = model_cls.add(request_json)
            res_data = model_to_dict(data, to_json_option)

            res_log_data = get_log_data(res_data)
            log_operation(module, 'add', success, req_log_data, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Add {} data'.format(class_name), req_log_data, success, res_log_data))

            return create_response(success, res_data)

    if 'delete' in routers:
        @api_blueprint.route(url_prefix + '/<did>/', methods=['DELETE'])
        @rest_permission_required(module, 'delete')
        @gen_route_method('delete', url_prefix)
        def delete(did):  # @2023-01-12 add 'path' converter type，@2023-02-07 add '/' to the end to fix request issues ending with /, @2023-03-02 remove path converter
            """
            delete model data by id
            :return:
            """
            success, data = model_cls.delete(did)
            res_data = model_to_dict(data, to_json_option)

            res_log_data = get_log_data(res_data)
            log_operation(module, 'delete', success, did, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Delete {} data'.format(class_name), did, success, res_log_data))

            return create_response(success, res_data)

    if 'update' in routers:
        @api_blueprint.route(url_prefix + '/', methods=['PATCH'])
        @api_blueprint.route(url_prefix + '/<did>/', methods=['PATCH'])  # @2023-02-14 add primary key, @2023-03-02 remove path converter
        @rest_permission_required(module, 'update')
        @gen_route_method('update', url_prefix)
        def update(did=None):
            """
            Update the model data by the json.
            The priority of the primary key in the url is higher than that in the body.
            :return:
            """
            request_json = request.json
            if did is not None:
                request_json[model_cls.get_primary_field()] = did  # use pk in url
            req_log_data = json.dumps(request_json)

            success, data = model_cls.update(request_json)
            res_data = model_to_dict(data, to_json_option)

            res_log_data = get_log_data(res_data)
            log_operation(module, 'update', success, req_log_data, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Update {} data'.format(class_name), req_log_data, success, res_log_data))

            return create_response(success, res_data)

    # if 'update' in routers:
    #     @api_blueprint.route(url_prefix + '/', methods=['PUT'])
    #     @rest_permission_required(module, 'update')
    #     @gen_route_method('update_put', url_prefix)
    #     def update():
    #         """
    #         todo
    #         Update the model data by the json in put mode.
    #         The difference between put and patch is that patch is partial update, and put is full update.            """
    #         pass

    if 'upsert' in routers:
        @api_blueprint.route(url_prefix + '/upsert/', methods=['POST'])
        @rest_permission_required(module, 'upsert')
        @gen_route_method('upsert', url_prefix)
        def upsert():
            """
            Update the model data by the json.
            :return:
            """
            request_json = request.json
            req_log_data = json.dumps(request_json)

            if request_json.get('id'):
                action = "update"
                success, data = model_cls.update(request_json)
            else:
                action = "add"
                success, data = model_cls.add(request_json)

            res_data = model_to_dict(data, to_json_option)
            res_log_data = get_log_data(res_data)
            log_operation(module, action, success, req_log_data, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Upsert {} data'.format(class_name), req_log_data, success, res_log_data))

            return create_response(success, res_data)

    if 'query' in routers:
        @api_blueprint.route(url_prefix + '/', methods=['GET'])
        @api_blueprint.route(url_prefix + '/<did>/', methods=['GET'])  # @2023-02-13 add query by primary key, @2023-03-02 remove path converter
        @rest_permission_required(module)
        @gen_route_method('query', url_prefix)
        def query(did=None):
            """
            Query all the model data or specified data.
            if primary key is None, return all the data.
            :return:
            """
            if did is None:
                success, data = model_cls.query_all()
            else:
                try:
                    data = model_cls.query_by_pk(did)
                    if data:
                        success, data = True, data
                    else:
                        success, data = False, res_status_codes.db_data_not_found
                except Exception as e:
                    flaskz_logger.exception(e)
                    success, data = False, res_status_codes.db_query_err

            res_data = model_to_dict(data, to_json_option)
            flaskz_logger.debug(get_rest_log_msg('Query {} data'.format(class_name), did, success, res_data))
            return create_response(success, res_data)

    if 'query_pss' in routers:
        @api_blueprint.route(url_prefix + '/query_pss/', methods=['GET', 'POST'])
        @rest_permission_required(module)
        @gen_route_method('query_pss', url_prefix)
        def query_pss():
            """
            Query data by search, pagination and sort condition.
            :return:
            """
            request_json = request.json
            req_log_data = json.dumps(request_json)

            success, data = model_cls.query_pss(get_pss(model_cls, request_json))
            if success is True:
                data['data'] = model_to_dict(data.get('data', []), to_json_option)

            flaskz_logger.debug(get_rest_log_msg('Query pss {} data'.format(class_name), req_log_data, success, data))
            return create_response(success, data)

    if multiple_option and 'query_multiple' in routers:
        @api_blueprint.route(url_prefix + '/query_multiple/', methods=['GET'])
        @rest_permission_required(module)
        @gen_route_method('query_multiple', url_prefix)
        def query_multiple():
            """
            Query multiple model data
            ex)
            multiple_option={
                'users': User,
                'roles': {
                    'model_cls': Role,
                    'option': {
                        # 'cascade': 1,
                        'includes': ['id', 'name']
                    }
                }
            }
            :return:
            """
            model_cls_list = []
            multiple_list = []
            for key in multiple_option:
                item = multiple_option[key]
                item_option = {}
                m_cls = None
                if is_dict(item):  # 'roles': {'model_cls': Role,'option': {'includes': ['id', 'name']}}
                    m_cls = item.get('model_cls')
                    item_option = item.get('option')
                elif isinstance(item, type) and issubclass(item, ModelMixin):  # 'users': User,
                    m_cls = item
                    item_option = {}
                if m_cls and issubclass(m_cls, ModelMixin):
                    model_cls_list.append(m_cls)
                    multiple_list.append({
                        'field': key,
                        'option': item_option
                    })

            result = query_multiple_model(*model_cls_list)

            if type(result) is tuple:
                success = False
                res_data = model_to_dict(result[1])
            else:
                success = True
                res_data = {}
                for index, item in enumerate(multiple_list):
                    res_data[item.get('field')] = model_to_dict(result[index], item.get('option'))
            flaskz_logger.debug(get_rest_log_msg('Query multiple {} data'.format(class_name), None, success, res_data))
            return create_response(success, res_data)
    return api_blueprint


# def _log_operation(*args, **kwargs):
#     logging_callback = get_current_model_rest_manager_callback('logging_callback')
#     if logging_callback:
#         logging_callback(*args, **kwargs)


from ._mgmt import *
from ._util import *
