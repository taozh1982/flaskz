## 关于

*Flaskz*是*Flask*和*SQLAlchemy ORM*的扩展，主要用于web应用的开发，可以快速灵活的实现各种业务场景和提供API。

## 使用

1. [☞数据库初始化&常用函数](http://zhangyiheng.com/blog/articles/py_flaskz_model_init.html)
2. [☞数据模型扩展类](http://zhangyiheng.com/blog/articles/py_flaskz_model_mixin.html)
3. [☞API封装、访问权限控制和系统日志](http://zhangyiheng.com/blog/articles/py_flaskz_api.html)
4. [☞常用函数](http://zhangyiheng.com/blog/articles/py_flaskz_utils.html)
5. [☞基于Flaskz的管理系统开发模板 Flaskz-admin](http://zhangyiheng.com/blog/articles/py_flaskz_admin.html)
6. [☞使用手册](http://zhangyiheng.com/blog/articles/py_flaskz_manual.html)

## 规范

- 标准化/规范化/配置灵活
- 写好注释和文档
- 消除告警提示

## 版本

+ **0.8** `2022/08/01`
    + [A] `BaseModelMixin`和`ModelMixin`模型扩展类添加没有flask上下文环境时的使用支持
    + [A] 添加`flaskz.ext`包用于存放扩展工具类，请注意ext包中的代码依赖的第三方包，不在flaskz的install_requires中，需要单独安装
    + [C] 将`flask.utils.RSACipher`和`flask.utils.AESCipher`类所在的`cypher.py`文件移到了`flaskz.ext`包中
+ **0.7** `2022/06/01`
    + [A] 添加`flask.utils.RSACipher`和`flask.utils.AESCipher`类用于加密&解密，需要安装`pycryptodome`包
    + [A] 添加`flask.utils.append_url_search_params`函数，用于向url中添加search参数
+ **0.6** `2022/05/06`
    + [F] 修复当数据模型relationship中设置`lazy=joined`时，排序引起的`"Can't resolve label reference"`问题
    + [F] 修复`merge_dict`方法，因使用iteritems导致的bug
    + [F] 修复`forward_request`方法，因请求没有设置`Content-Type=application/json`，获取json时引发的`BadRequest('Content-Type was not 'application/json')`异常
    + [F] 修复未调用`init_log`初始化，调用flaskz_logger时，引起的`NameError(name '_flaskz_logger' is not defined)`问题
+ **0.3** `2021/11/26`
    + [A] 添加`FLASKZ_LOGGER_DISABLED`参数，用于控制flaskz_logger的启用和禁用
    + [A] 添加使用文档
    + [C] 修改`flaskz.utils.forward_request`函数逻辑，如果url_params参数为空时，会把`request.view_args`作为`url_params`参数来调用`api_request`
+ **0.2**
    + [F] 修复`query_multiple_model`函数bug
    + [C] 对部分参数名进行规范化调整
+ **0.1**
    + 发布