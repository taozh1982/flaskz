## 关于

*Flaskz*是*Flask*和*SQLAlchemy ORM*的扩展工具集, 主要用于web应用的开发, 可以快速灵活的实现各种业务场景并提供API。

## 使用

1. [☞数据库初始化&常用函数](http://zhangyiheng.com/blog/articles/py_flaskz_model_init.html)
2. [☞数据模型扩展类](http://zhangyiheng.com/blog/articles/py_flaskz_model_mixin.html)
3. [☞API封装、访问权限控制和系统日志](http://zhangyiheng.com/blog/articles/py_flaskz_api.html)
4. [☞常用函数](http://zhangyiheng.com/blog/articles/py_flaskz_utils.html)
5. [☞基于Flaskz的管理系统开发模板 Flaskz-admin](http://zhangyiheng.com/blog/articles/py_flaskz_admin.html)
6. [☞使用手册](http://zhangyiheng.com/blog/articles/py_flaskz_manual.html)

## 版本

- **1.8.0** `2024/06/01`
    - [A] 扩展`flaskz.rest`路由生成模块
        - 添加`register_model_bulk_route`函数, 用于生成指定数据模型的批量增删改路由
        - 添加`register_model_bulk_add_route`函数, 用于生成指定数据模型的批量添加路由
        - 添加`register_model_bulk_delete_route`函数, 用于生成指定数据模型的批量删除路由
        - 添加`register_model_bulk_update_route`函数, 用于生成指定数据模型的批量更新路由
    - [A] 添加`flaskz.utils.request`函数(替代`flaskz.utils.api_request`函数)
    - [A] 添加`flaskz.utils.json_dumps`函数以序列化对象为JSON字符串
    - [F] 修复`flaskz.ext.ssh.SSH`中`_pre_commands_run`的未赋值问题
- **1.7.3** `2024/05/01`
    - [C] `flaskz.utils.ins_to_dict`函数返回的dict中包含值为`None`的键值
    - [A] `BaseModelMixin.to_dict`方法的`option`参数添加`relationships`选项，用于自定义是否查询关联关系
    - [A] `FLASKZ_DATABASE_SESSION_KWARGS`配置参数添加`reusable_in_flask_g`选项, 用于设置是否在`flask.g`中缓存&复用`session`对象(默认复用)
    - [C] `flaskz.ext.ssh`返回值保留文本两侧的空格
    - [A] `flaskz.ext.ssh.SSH`添加`pre_commands`参数, 用于在命令执行之前预先执行控制相关命令
- **1.7.2** `2024/02/01`
    - [A] `flaskz.models.parse_pss`函数支持`like_columns`参数, 用于定义模糊查询列(默认使用模型类的like_columns)
    - [A] `flaskz.utils.api_request`函数添加`http_kwargs`参数，用于设置http请求参数
- **1.7.1** `2024/01/05`
    - [F] 修复SQLAlchemy<2.0.0版本时, `flaskz.models._util.py`中`BinaryExpression`类的导入问题
- **1.7.0** `2024/01/01`
    - [C] `SQLAlchemy`依赖的版本从`>=1.3.13(EOL)`升级到`>=1.4.0(Maintenance)`
    - [A] `BaseModelMixin.query_pss`方法支持`relationship`的查询和排序
    - [A] `flaskz.models.parse_pss`函数支持`relationship`的查询和排序参数解析
- **1.6.4** `2023/12/01`
    - [A] `BaseModelMixin`添加`refresh`方法, 用于更新当前模型对象
    - [A] 添加`flaskz.models.refresh_instance`函数, 用于更新模型对象/列表
    - [A] `model_to_dict`函数的`option`参数添加`filter`选项, 用于过滤模型对象列表
    - [A] `flaskz.rest.register_model_query_pss_route`路由生成函数添加`get_pss_config`参数, 用于自定义pss查询参数
    - [A] `flaskz.ext.ssh`添加`ssh_run_command`和`ssh_run_command_list`函数
    - [A] `flaskz.ext.ssh.SSH`添加`connect_kwargs`和`channel_kwargs`参数以自定义connect和channel参数
    - [A] `flaskz.ext.ssh.SSH`设置`timeout`参数的默认值为`10`
- **1.6.3** `2023/09/01`
    - [A] 添加`FLASKZ_DATABASE_SESSION_KWARGS`配置参数, 用于自定义`DBSession`参数
    - [C] `BaseModelMixin.add_db`和`BaseModelMixin.update_db`方法添加`refresh`操作, 以返回跟数据库同步的instance对象
    - [A] `flaskz.rest.register_model_*`路由生成函数添加路由`endpoint`参数
- **1.6.2** `2023/07/06`
    - [F] 修复`flaskz.utils._request_args.py`中`import parse_pss as get_pss`的导入问题
- **1.6.1** `2023/07/01`
    - [C] `flaskz.utils.get_pss`(`flaskz.models.parse_pss`)函数返回项由SQL字符串拼接改为参数化模式以预防SQL注入
    - [A] 添加`flaskz.utils.run_at`函数用于执行定时函数
- **1.6** `2023/06/16`
    - [A] `BaseModelMixin`添加`count`方法, 用于数量查询(全量/条件)
    - [A] `BaseModelMixin`添加`clear_db`方法, 用于清空数据
    - [A] `BaseModelMixin.query_pss`方法支持`GROUP BY`分组
    - [A] `flaskz.ext.ssh`添加对Paramiko>=3.0.0版本的支持
    - [A] `flaskz.ext.ssh.SSH`添加`secondary_password`和`recv_endswith`参数
- **1.5.3** `2023/06/01`
    - [F] `flaskz.utils.api_request`函数的`url_params`参数仅用于url中的`{变量}`替换而不添加查询字符串
    - [A] `flaskz.utils.api_request`函数添加`url_search_params`参数用于添加url查询字符串
- **1.5.2** `2023/05/17`
    - [C] `db_session`上下文管理器自动关闭非缓存session
    - [F] 修复`BaseModelMixin.get_query_default_order`默认排序在`query_pss`方法中不起作用的问题
- **1.5** `2023/05/01`
    - [A] 扩展`flaskz.rest`路由生成模块
        - 添加`register_model_route`函数, 可用于生成指定数据模型的CRUD等路由
        - 添加`register_model_add_route`函数, 可用于生成指定数据模型的添加路由
        - 添加`register_model_delete_route`函数, 可用于生成指定数据模型的删除路由
        - 添加`register_model_update_route`函数, 可用于生成指定数据模型的更新路由
        - 添加`register_model_upsert_route`函数, 可用于生成指定数据模型的添加/更新路由
        - 添加`register_model_query_route`函数, 可用于生成指定数据模型的全量查询路由
        - 添加`register_model_query_pss_route`函数, 可用于生成指定数据模型的条件查询(分页+搜索+排序)路由
        - 添加`register_models_query_route`函数, 可用于生成多个数据模型的全量查询路由
    - [A] `ModelMixin.query_pss`方法支持多列排序
    - [A] `flaskz.models.init_model`和`flaskz.log.init_log`函数添加对`Class`类型参数的支持
    - [A] `BaseModelMixin.delete_db`方法添加对`dict`类型参数的支持
    - [A] `flaskz.utils`添加`cls_to_dict`函数, 用于生成类属性的dict对象
    - [C] `BaseModelMixin.bulk_delete`方法会删除符合条件的所有数据(此前版本只删除第一个)
- **1.3.1** `2023/03/02`
    - [C] `init_model_rest_blueprint`函数生成的路由, 移除参数`path`类型转换, 以解决Flask<2.2.3版本不会将结尾不带`/`的请求重定向到带`/`路由的问题
- **1.3** `2023/03/01`
    - [A] `init_model_rest_blueprint`函数生成的query路由, 添加对单个数据的查询功能(`[GET]url_prefix/did/`)
    - [A] `init_model_rest_blueprint`函数生成的update路由, 添加URL主键支持(`[PATCH]url_prefix/did/`)
    - [C] `init_model_rest_blueprint`函数生成的delete路由, 结尾添加`/`, 用于支持以`/`结尾的URL删除请求(`[DELETE]url_prefix/did/`)
    - [A] 添加`FLASKZ_DATABASE_ENGINE_KWARGS`参数, 用于自定义`engine`参数
- **1.2** `2023/02/01`
    - [A] 添加`FLASKZ_DATABASE_POOL_PRE_PING`参数, 用于设置engine的`pool_pre_ping`参数
    - [A] `init_model`函数添加数据库连接异常处理和重新连接
    - ~~[C] `init_model_rest_blueprint`函数生成的删除路由URL中的id参数添加`path`类型转换(v1.3.1已移除)~~
- **1.1** `2023/01/01`
    - [F] 修复`BaseModelMixin`的`update_db`和`delete_db`方法在非Flask应用或没有Flask应用上下文时的操作失败问题
- **1.0** `2022/12/01`
    - [A] 添加`flaskz.utils.set_timeout`和`flaskz.utils.set_interval`函数用于延迟和周期性函数执行
    - [A] `flaskz.ext.ssh.SSH`添加`timeout`参数以设置超时时间(登录&命令执行)
    - [F] 修复`BaseModelMixin.bulk_delete`方法因某条数据删除失败导致的操作中断和部分删除问题
- **0.9** `2022/10/01`
    - [A] 添加`flaskz.auth`包, 提供了JWS授权功能
    - [A] 添加`flaskz.ext.ssh`, 提供了ssh相关功能(`pip install paramiko`)
- **0.8** `2022/08/01`
    - [A] `BaseModelMixin`和`ModelMixin`模型扩展类添加没有Flask上下文环境时的使用支持
    - [A] 添加`flaskz.ext`包用于存放扩展工具类, 请注意ext包中的代码依赖的第三方包, 不在flaskz的install_requires中, 需要单独安装
    - [C] 将`flaskz.utils.RSACipher`和`flaskz.utils.AESCipher`类所在的`cypher.py`文件移到了`flaskz.ext`包中
- **0.7** `2022/06/01`
    - [A] 添加`flaskz.utils.RSACipher`和`flaskz.utils.AESCipher`类用于加密&解密, 需要安装`pycryptodome`包
    - [A] 添加`flaskz.utils.append_url_search_params`函数, 用于向url中添加search参数
- **0.6** `2022/05/06`
    - [F] 修复当数据模型relationship中设置`lazy=joined`时, 排序引起的`"Can't resolve label reference"`问题
    - [F] 修复`merge_dict`方法, 因使用iteritems导致的bug
    - [F] 修复`forward_request`方法, 因请求没有设置`Content-Type=application/json`, 获取json时引发的`BadRequest('Content-Type was not 'application/json')`异常
    - [F] 修复未调用`init_log`初始化, 调用flaskz_logger时, 引起的`NameError(name '_flaskz_logger' is not defined)`问题
- **0.3** `2021/11/26`
    - [A] 添加`FLASKZ_LOGGER_DISABLED`参数, 用于控制flaskz_logger的启用和禁用
    - [A] 添加使用文档
    - [C] 修改`flaskz.utils.forward_request`函数逻辑, 如果url_params参数为空时, 会把`request.view_args`作为`url_params`参数来调用`api_request`
- **0.2** `2021/11/12`
    - [F] 修复`query_multiple_model`函数bug
    - [C] 对部分参数名进行规范化调整
- **0.1** `2021/10/26`
    - 发布