## 关于

Flaskz是Flask和SQLAlchemy ORM的扩展，主要用于web应用的开发，可以快速灵活的实现各种业务场景和提供API。

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
- 尽量消除IDE中的告警提示
- 永远不要写临时代码
- 能用单引号的地方不要用双引号

## 版本

+ **0.6** `2022/05/06`
    + [修复]数据模型relationship中设置lazy=joined，排序引起的"Can't resolve label reference"问题
    + [修复]merge_dict方法，使用iteritems导致的bug
    + [修复]forward_request方法，因为请求没有设置Content-Type=application/json导致获取json引发BadRequest('Content-Type was not 'application/json')异常
    + [修复]没有调用init_log初始化，调用flaskz_logger引起的NameError(name '_flaskz_logger' is not defined)
+ **0.3** `2021/11/26`
    + [添加]FLASKZ_LOGGER_DISABLED参数
    + [添加]使用文档
    + [修改]flaskz.utils.forward_request函数，如果url_params参数为空，默认会把request.view_args作为url_params参数来调用api_request
+ **0.2**
    + [修复]query_multiple_model Bug
    + [修改]对部分参数名进行规范化调整
+ **0.1**
    + 发布