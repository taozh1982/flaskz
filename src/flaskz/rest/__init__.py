import json

from flask import request

from .. import res_status_codes
from ..log import flaskz_logger, get_log_data
from ..models import model_to_dict, query_all_models, ModelMixin, parse_pss
from ..utils import get_list, is_dict, create_response, get_request_json


def init_model_rest_blueprint(model_cls, api_blueprint, url_prefix, module, routers=None, to_json_option=None, multiple_option=None):
    """
    ** Deprecated, please use register_model_route **

    Append rest api route to the api blueprint for the specified model class.

    Example:
        init_model_rest_blueprint(User, sys_mgmt_bp, '/user', 'user', multiple_option={
            'users': User,
            'roles': {
                'model_cls': Role,
                'option': {
                    'include': ['id', 'name']
                }
            }
        })

    :param to_json_option: The option used to return json, fields/cascade. ex){'cascade': 1}
    :param url_prefix: Api url path,ex) '/roles'
    :param module: The module name,ex) 'roles'
    :param api_blueprint:
    :param model_cls: The specified model class.
    :param routers: The api router list, ex)['query', 'query_pss', 'add', 'update', 'delete']
    :param multiple_option:

    :return: api_blueprint
    """
    if to_json_option is None:
        to_json_option = {}

    routers = get_list(routers, ['query', 'query_pss', 'query_multiple', 'add', 'update', 'upsert', 'delete'])

    if 'add' in routers:
        register_model_add_route(api_blueprint, model_cls, url_prefix, module, to_json_option=to_json_option)

    if 'delete' in routers:
        register_model_delete_route(api_blueprint, model_cls, url_prefix, module, to_json_option=to_json_option)

    if 'update' in routers:
        register_model_update_route(api_blueprint, model_cls, url_prefix, module, to_json_option=to_json_option)

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
        register_model_upsert_route(api_blueprint, model_cls, url_prefix, module, to_json_option=to_json_option)

    if 'query' in routers:
        register_model_query_route(api_blueprint, model_cls, url_prefix, module, to_json_option=to_json_option)

    if 'query_pss' in routers:
        register_model_query_pss_route(api_blueprint, model_cls, url_prefix, module, to_json_option=to_json_option, rule_suffix='query_pss')

    if multiple_option and 'query_multiple' in routers:
        register_models_query_route(api_blueprint, multiple_option, url_prefix, module, rule_suffix='query_multiple')

    return api_blueprint


def register_model_route(app, model, rule, module=None, types=None, multi_models=None, to_json_option=None, get_pss_config=None, strict_slash=True):
    """
    Register url rules for the specified model class to the application/blueprint.

    .. versionadded:: 1.5
    .. versionupdated::
        1.6.4 - add get_pss_config parameter

    Example:
        register_model_route(api_bp, User, 'users', 'users')

    :param app: Flask application / Blueprint instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param types: The types of the route, default is ['query', 'pss', 'multi', 'add', 'update', 'upsert', 'delete']
    :param multi_models: The multiple DB model classes
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param get_pss_config: The callback function to custom pss query config
    :param strict_slash: If not false, the rule url will end with slash
    :return:
    """
    if type(get_pss_config) is bool:  # version match
        strict_slash = get_pss_config
        get_pss_config = None

    types = get_list(types, ['query', 'pss', 'multi', 'add', 'update', 'upsert', 'delete'])
    if 'add' in types:
        register_model_add_route(app, model, rule, module, to_json_option=to_json_option, strict_slash=strict_slash)
    if 'delete' in types:
        register_model_delete_route(app, model, rule, module, to_json_option=to_json_option, strict_slash=strict_slash)
    if 'update' in types:
        register_model_update_route(app, model, rule, module, to_json_option=to_json_option, strict_slash=strict_slash)
    if 'upsert' in types:
        register_model_upsert_route(app, model, rule, module, to_json_option=to_json_option, strict_slash=strict_slash)
    if 'query' in types:
        register_model_query_route(app, model, rule, module, to_json_option=to_json_option, strict_slash=strict_slash)
    if 'pss' in types:
        register_model_query_pss_route(app, model, rule, module, to_json_option=to_json_option, strict_slash=strict_slash, get_pss_config=get_pss_config)
    if multi_models and ('multi' in types or 'multiple' in types):
        register_models_query_route(app, multi_models, rule, module)
    if 'bulk_add' in types:
        register_model_bulk_add_route(app, model, rule, module, strict_slash=strict_slash)
    if 'bulk_delete' in types:
        register_model_bulk_delete_route(app, model, rule, module, strict_slash=strict_slash)
    if 'bulk_update' in types:
        register_model_bulk_update_route(app, model, rule, module, strict_slash=strict_slash)
    return app


def register_model_bulk_route(app, model, rule, module=None, types=None, with_relationship=False, strict_slash=True):
    """
    Register url rules for bulk operations of the specified model class to the application/blueprint.

    .. versionadded:: 1.8
    .. versionupdated::
        1.8.1   - add with_relationship param

    Example:
        register_model_bulk_route(api_bp, User, 'users', 'users')

    :param app: Flask application / Blueprint instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param types: The types of the route, default is ['bulk_add', 'bulk_delete', 'bulk_update']
    :param with_relationship: If True, the relationship data will be added/updated in bulk, default is False
    :param strict_slash: If not False, the rule url will end with slash
    :return:
    """
    types = get_list(types, ['bulk_add', 'bulk_delete', 'bulk_update'])
    if 'bulk_add' in types:
        register_model_bulk_add_route(app, model, rule, module, with_relationship=with_relationship, strict_slash=strict_slash)
    if 'bulk_delete' in types:
        register_model_bulk_delete_route(app, model, rule, module, strict_slash=strict_slash)
    if 'bulk_update' in types:
        register_model_bulk_update_route(app, model, rule, module, with_relationship=with_relationship, strict_slash=strict_slash)
    return app


def register_model_add_route(app, model, rule, module=None, action='add', methods=None, to_json_option=None, strict_slash=True, endpoint=None):
    """
    Register a add type URL rule for the specified model class to the application/blueprint.

    Examples:
        register_model_add_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)add
    :param methods: The methods of the route, default is ['POST']
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param strict_slash: If not false, the rule url will end with slash
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['POST']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash)

    @app.route(base_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('add', base_rule)
    def add():
        request_json = request.json
        req_log_data = json.dumps(request_json)

        success, data = model.add(request_json)
        res_data = model_to_dict(data, to_json_option)

        res_log_data = get_log_data(res_data)
        log_operation(module, 'add', success, req_log_data, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Add {} data'.format(model.get_class_name()), req_log_data, success, res_log_data))

        return create_response(success, res_data)


def register_model_delete_route(app, model, rule, module=None, action='delete', methods=None, to_json_option=None, strict_slash=True, endpoint=None):
    """
    Register a delete type URL rule for the specified model class to the application/blueprint.

    .. versionupdated::
        1.2   - add path converter of the did
        1.3.1 - remove path converter of the did(Flask<2.2.3 path converter doesn't redirect to trailing slash)

    Examples:
        register_model_delete_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)delete
    :param methods: The methods of the route, default is ['DELETE']
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param strict_slash: If not false, the rule url will end with slash
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['DELETE']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, did_suffix='<did>')

    @app.route(did_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('delete', base_rule)
    def delete(did):
        success, data = model.delete(did)
        res_data = model_to_dict(data, to_json_option)

        res_log_data = get_log_data(res_data)
        log_operation(module, 'delete', success, did, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Delete {} data'.format(model.get_class_name()), did, success, res_log_data))

        return create_response(success, res_data)


def register_model_update_route(app, model, rule, module=None, action='update', methods=None, to_json_option=None, strict_slash=True, endpoint=None):
    """
    Register update type URL rule for the specified model class to the application/blueprint.
    The priority of the primary key in the url is higher than that in the body.

    Examples:
        register_model_update_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)update
    :param methods: The methods of the route, default is ['PATCH']
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param strict_slash: If not false, the rule url will end with slash
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['PATCH']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, did_suffix='<did>')

    @app.route(base_rule, methods=methods, endpoint=endpoint)
    @app.route(did_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('update', base_rule)
    def update(did=None):
        request_json = request.json
        if did is not None:
            request_json[model.get_primary_field()] = did  # use pk in url
        req_log_data = json.dumps(request_json)

        success, data = model.update(request_json)
        res_data = model_to_dict(data, to_json_option)

        res_log_data = get_log_data(res_data)
        log_operation(module, 'update', success, req_log_data, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Update {} data'.format(model.get_class_name()), req_log_data, success, res_log_data))

        return create_response(success, res_data)


def register_model_upsert_route(app, model, rule, module=None, action='upsert', methods=None, to_json_option=None, strict_slash=True, rule_suffix='upsert', endpoint=None):
    """
    Register a upsert type URL rule for the specified model class to the application/blueprint.
    If primary key value is in json, perform an update action, otherwise perform an add action.

    Examples:
        register_model_upsert_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)update
    :param methods: The methods of the route, default is ['PATCH']
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param strict_slash: If not false, the rule url will end with slash
    :param rule_suffix: The upsert suffix, default is 'upsert'
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    """
    methods = methods or ['POST']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, rule_suffix=rule_suffix)

    @app.route(suffix_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('upsert', base_rule)
    def upsert():
        request_json = request.json
        req_log_data = json.dumps(request_json)

        if request_json.get(model.get_primary_field()):
            upsert_action = "update"
            success, data = model.update(request_json)
        else:
            upsert_action = "add"
            success, data = model.add(request_json)

        res_data = model_to_dict(data, to_json_option)
        res_log_data = get_log_data(res_data)
        log_operation(module, upsert_action, success, req_log_data, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Upsert {} data'.format(model.get_class_name()), req_log_data, success, res_log_data))

        return create_response(success, res_data)


def register_model_query_route(app, model, rule, module=None, action=None, methods=None, to_json_option=None, strict_slash=True, endpoint=None):
    """
    Register query type URL rule for the specified model class to the application/blueprint.

    Examples:
        register_model_query_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, default is None(only check module permission)
    :param methods: The methods of the route, default is ['GET']
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param strict_slash: If not false, the rule url will end with slash
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['GET']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, did_suffix='<did>')

    @app.route(base_rule, methods=methods, endpoint=endpoint)
    @app.route(did_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('query', base_rule)
    def query(did=None):
        if did is None:
            success, data = model.query_all()
        else:
            try:
                data = model.query_by_pk(did)
                if data:
                    success, data = True, data
                else:
                    success, data = False, res_status_codes.db_data_not_found
            except Exception as e:
                flaskz_logger.exception(e)
                success, data = False, res_status_codes.db_query_err

        res_data = model_to_dict(data, to_json_option)
        flaskz_logger.debug(get_rest_log_msg('Query {} data'.format(model.get_class_name()), did, success, res_data))
        return create_response(success, res_data)


def register_model_query_pss_route(app, model, rule, module=None, action=None, methods=None, to_json_option=None, strict_slash=True, rule_suffix='pss', get_pss_config=None,
                                   endpoint=None):
    """
    Register pss query URL rule for the specified model class to the application/blueprint.
    pss = paging + search + sort

    .. versionadded::
        1.6.4 - add get_pss_config param

    Examples:
        register_model_query_pss_route(api_blueprint, User, 'users', 'users', get_pss_config=append_search_config)

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, default is None(only check module permission)
    :param methods: The methods of the route, default is ['GET', 'POST']
    :param to_json_option: The option to return the json, ex){'cascade': 1}
    :param strict_slash: If not false, the rule url will end with slash
    :param rule_suffix: The pss suffix, default is 'query_pss'
    :param get_pss_config: Callback function used to generate pss config.
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['GET', 'POST']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, rule_suffix=rule_suffix)

    @app.route(suffix_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('query_pss', base_rule)
    def query_pss():
        request_json = get_request_json({})  # @2023-06-15, request.json --> get_request_json({})
        req_log_data = json.dumps(request_json)

        if callable(get_pss_config):  # @2023-10-13 add
            request_json = get_pss_config(request_json)  # @2023-10-23 fix, get_pss_config-->request_json

        success, data = model.query_pss(parse_pss(model, request_json))
        if success is True:
            data['data'] = model_to_dict(data.get('data', []), to_json_option)

        flaskz_logger.debug(get_rest_log_msg('Query pss {} data'.format(model.get_class_name()), req_log_data, success, data))
        return create_response(success, data)


def register_models_query_route(app, models, rule, module=None, action=None, methods=None, strict_slash=True, rule_suffix='multi', endpoint=None):
    """
    Register query multi models URL rule to the application/blueprint.
    pss = paging + search + sort

    Examples:
        register_models_query_route(api_blueprint,
                                 {
                                     'users': User,
                                     'roles': {
                                         'model_cls': Role,
                                         'option': {
                                             # 'cascade': 1,
                                             'include': ['id', 'name']
                                             # 'filter': lambda ins: ins.type == 'local'
                                         }
                                     }
                                 })

    :param app: Flask application / Blueprints instance
    :param models: The multiple DB model classes,
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, default is None(only check module permission)
    :param methods: The methods of the route, default is ['GET', 'POST']
    :param strict_slash: If not false, the rule url will end with slash
    :param rule_suffix: The pss suffix, default is 'multi'
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)

    :return:
    """
    methods = methods or ['GET']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, rule_suffix=rule_suffix)

    @app.route(suffix_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('query_multi', base_rule)
    def query_multi():
        model_cls_list = []
        multi_list = []
        for key in models:
            item = models[key]
            item_option = {}
            m_cls = None
            if is_dict(item):  # 'roles': {'model': Role,'option': {'include': ['id', 'name']}}
                m_cls = item.get('model_cls') or item.get('model')
                item_option = item.get('option') or item.get('to_json_option')
            elif isinstance(item, type) and issubclass(item, ModelMixin):  # 'users': User,
                m_cls = item
                item_option = {}
            if m_cls and issubclass(m_cls, ModelMixin):
                model_cls_list.append(m_cls)
                multi_list.append({
                    'field': key,
                    'option': item_option
                })
        result = query_all_models(*model_cls_list)

        if type(result) is tuple:
            success = False
            res_data = model_to_dict(result[1])
        else:
            success = True
            res_data = {}
            for index, item in enumerate(multi_list):
                res_data[item.get('field')] = model_to_dict(result[index], item.get('option'))

        flaskz_logger.debug(get_rest_log_msg('Query multi {} data'.format(model_cls_list), None, success, res_data))
        return create_response(success, res_data)


def register_model_bulk_add_route(app, model, rule, module=None, action='add', methods=None, with_relationship=False, strict_slash=True, rule_suffix='bulk', endpoint=None):
    """
    Register bulk add type URL rule for the specified model class to the application/blueprint.

    .. versionadded:: 1.8
    .. versionupdated::
        1.8.1   - add with_relationship param

    Examples:
        register_model_bulk_add_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)add
    :param methods: The methods of the route, default is ['POST']
    :param with_relationship: If True, the relationship data will be added in bulk, default is False
    :param strict_slash: If not False, the rule url will end with slash
    :param rule_suffix: The upsert suffix, default is 'bulk-add'
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['POST']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, rule_suffix=rule_suffix)

    @app.route(suffix_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('bulk_add', base_rule)
    def bulk_add():
        request_json = request.json
        req_log_data = json.dumps(request_json)
        try:
            model.bulk_add(request_json, with_relationship=with_relationship)
            success, res_data = True, request_json
        except Exception as e:
            flaskz_logger.exception(e)
            success, res_data = False, res_status_codes.db_add_err

        res_log_data = get_log_data(res_data)
        log_operation(module, 'add', success, req_log_data, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Bulk add {} data'.format(model.get_class_name()), req_log_data, success, res_log_data))

        return create_response(success, res_data)


def register_model_bulk_delete_route(app, model, rule, module=None, action='delete', methods=None, strict_slash=True, rule_suffix='bulk', endpoint=None):
    """
    Register bulk delete type URL rule for the specified model class to the application/blueprint.

    .. versionadded:: 1.8

    Examples:
        register_model_bulk_delete_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)delete
    :param methods: The methods of the route, default is ['DELETE']
    :param strict_slash: If not false, the rule url will end with slash
    :param rule_suffix: The upsert suffix, default is 'bulk-delete'
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['DELETE']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, did_suffix='<ids>', rule_suffix=rule_suffix)

    @app.route(suffix_rule, methods=methods, endpoint=endpoint)
    @app.route(did_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('bulk_delete', base_rule)
    def bulk_delete(ids=None):
        req_log_data = ids
        if ids is None:
            request_json = request.json
            req_log_data = json.dumps(request_json)
            ids = request_json
            if type(request_json) is dict:
                ids = request_json.get('ids') or request_json.get('id', [])
        else:
            ids = ids.split(',')
        try:
            success, res_data = True, model.bulk_delete(ids)
        except Exception as e:
            flaskz_logger.exception(e)
            success, res_data = False, res_status_codes.db_delete_err

        res_log_data = get_log_data(res_data)
        log_operation(module, 'delete', success, req_log_data, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Bulk delete {} data'.format(model.get_class_name()), req_log_data, success, res_log_data))

        return create_response(success, res_data)


def register_model_bulk_update_route(app, model, rule, module=None, action='update', methods=None, with_relationship=False, strict_slash=True, rule_suffix='bulk', endpoint=None):
    """
    Register bulk update type URL rule for the specified model class to the application/blueprint.

    .. versionadded:: 1.8
    .. versionupdated::
        1.8.1   - add with_relationship param

    Examples:
        register_model_bulk_update_route(api_blueprint, User, 'users', 'users')

    :param app: Flask application / Blueprints instance
    :param model: The DB model class, ex)User
    :param rule: The URL rule string, ex)/users
    :param module: The module name for permission check, ex)users
    :param action: The action of the module for permission check, ex)update
    :param methods: The methods of the route, default is ['PATCH']
    :param with_relationship: If True, the relationship data will be updated in bulk, default is False
    :param strict_slash: If not False, the rule url will end with slash
    :param rule_suffix: The upsert suffix, default is 'bulk-update'
    :param endpoint: The name of the route endpoint, default is None(use view function name as endpoint name)
    :return:
    """
    methods = methods or ['PATCH']
    base_rule, did_rule, suffix_rule = _gen_route_rule(rule, strict_slash=strict_slash, rule_suffix=rule_suffix)

    @app.route(suffix_rule, methods=methods, endpoint=endpoint)
    @rest_permission_required(module, action)
    @gen_route_method('bulk_update', base_rule)
    def bulk_update():
        request_json = request.json
        req_log_data = json.dumps(request_json)
        try:
            model.bulk_update(request_json, with_relationship=with_relationship)
            success, res_data = True, request_json
        except Exception as e:
            flaskz_logger.exception(e)
            success, res_data = False, res_status_codes.db_update_err

        res_log_data = get_log_data(res_data)
        log_operation(module, 'update', success, req_log_data, res_log_data)
        flaskz_logger.info(get_rest_log_msg('Bulk update {} data'.format(model.get_class_name()), req_log_data, success, res_log_data))

        return create_response(success, res_data)


def _gen_route_rule(rule, *, strict_slash=True, did_suffix=None, rule_suffix=None):
    if not rule.startswith('/'):
        rule = '/' + rule
    base_rule = rule
    suffix_rule = rule
    did_rule = None

    if rule_suffix is not None:
        suffix_rule = rule = rule.rstrip('/') + '/' + rule_suffix

    if did_suffix is not None:
        did_rule = rule.rstrip('/') + '/' + did_suffix

    if strict_slash is not False:
        base_rule = base_rule.rstrip('/') + '/'
        suffix_rule = suffix_rule.rstrip('/') + '/'
        did_rule = did_rule.rstrip('/') + '/' if did_rule else None

    return base_rule, did_rule, suffix_rule


from ._mgmt import *
from ._util import *
