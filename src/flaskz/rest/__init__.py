import json

from flask import request

from ..log import flaskz_logger, get_log_data
from ..models import model_to_dict, query_multiple_model, ModelMixin
from ..utils import get_list, is_dict, create_response, get_pss


def init_model_rest_blueprint(model_cls, api_blueprint, url_prefix, module, routers=None, to_json_option=None, multiple_option=None):
    """
    Append rest api route to the api blueprint for the specified model class.
    :param to_json_option: The option used to return json, fields/cascade. ex){'cascade': 1}
    :param module: The module name,ex) role/menu
    :param url_prefix: Api url
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

            result = model_cls.add(request_json)
            res_data = model_to_dict(result[1], to_json_option)

            res_log_data = get_log_data(res_data)
            log_operation(module, 'add', result[0], req_log_data, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Add {} data'.format(class_name), req_log_data, result[0], res_log_data))

            return create_response(result[0], res_data)

    if 'delete' in routers:
        @api_blueprint.route(url_prefix + '/<did>', methods=['DELETE'])
        @rest_permission_required(module, 'delete')
        @gen_route_method('delete', url_prefix)
        def delete(did):
            """
            delete model data by id
            :return:
            """
            result = model_cls.delete(did)
            res_data = model_to_dict(result[1], to_json_option)

            res_log_data = get_log_data(res_data)
            log_operation(module, 'delete', result[0], did, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Delete {} data'.format(class_name), did, result[0], res_log_data))

            return create_response(result[0], res_data)

    if 'update' in routers:
        @api_blueprint.route(url_prefix + '/', methods=['PATCH'])
        @rest_permission_required(module, 'update')
        @gen_route_method('update', url_prefix)
        def update():
            """
            Update the model data by the json.
            :return:
            """
            request_json = request.json
            req_log_data = json.dumps(request_json)

            result = model_cls.update(request_json)
            res_data = model_to_dict(result[1], to_json_option)

            res_log_data = get_log_data(res_data)
            log_operation(module, 'update', result[0], req_log_data, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Update {} data'.format(class_name), req_log_data, result[0], res_log_data))

            return create_response(result[0], res_data)

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
        def update():
            """
            Update the model data by the json.
            :return:
            """
            request_json = request.json
            req_log_data = json.dumps(request_json)

            if request_json.get('id'):
                action = "update"
                result = model_cls.update(request_json)
            else:
                action = "add"
                result = model_cls.add(request_json)

            res_data = model_to_dict(result[1], to_json_option)
            res_log_data = get_log_data(res_data)
            log_operation(module, action, result[0], req_log_data, res_log_data)
            flaskz_logger.info(get_rest_log_msg('Upsert {} data'.format(class_name), req_log_data, result[0], res_log_data))

            return create_response(result[0], res_data)

    if 'query' in routers:
        @api_blueprint.route(url_prefix + '/', methods=['GET'])
        @rest_permission_required(module)
        @gen_route_method('query', url_prefix)
        def query():
            """
            Query all the model data
            :return:
            """
            result = model_cls.query_all()
            res_data = model_to_dict(result[1], to_json_option)

            flaskz_logger.debug(get_rest_log_msg('Query all {} data'.format(class_name), None, result[0], res_data))
            return create_response(result[0], res_data)

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

            result = model_cls.query_pss(get_pss(model_cls, request_json))
            res_data = result[1]
            if result[0] is True:
                res_data['data'] = model_to_dict(res_data['data'], to_json_option)

            flaskz_logger.debug(get_rest_log_msg('Query pss {} data'.format(class_name), req_log_data, result[0], res_data))
            return create_response(result[0], res_data)

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
            if result[0] is False:
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
