import inspect
import textwrap
from urllib import parse as urllib_parse

from flask import request as flask_request
from requests import Session, sessions
from requests.adapters import HTTPAdapter

from ._common import is_dict
from .. import res_status_codes
from ..log import flaskz_logger

__all__ = ['request', 'api_request', 'forward_request', 'append_url_search_params']

_session_request_kwargs = None


def api_request(url, method="GET", url_params=None, base_url="", raw_response=False, **kwargs):
    """
    Request an api.

   .. versionupdated::
        1.7.2 - add `http_kwargs` param to set http request parameters(HTTPAdapter)

    Example
        # post request
        api_request('req_url', 'POST', json=payload)
        api_request({'url': 'req_url', 'method': 'POST'}, json=payload)

        # get request
        api_request('req_url', headers={'Authorization': 'eyJhbGciOiJIUzUxMiIs......'})

        # base url
        api_request('req_url', base_url='base_url') # url --> 'base_url/req_url'

        # url_variables
        api_request('req_url/{id}/', url_variables={'id': 1}) # url --> 'req_url/1/'

        # url_search_params
        api_request('req_url', url_search_params={'id': 1}) # url --> 'req_url?id=1'

        # http_kwargs
        api_request('req_url', http_kwargs={ # --> HTTPAdapter parameters
            'pool_connections': 10, 'pool_maxsize': 100, 'max_retries': 10
        })

    :param url:
    :param method:
    :param url_params:
    :param raw_response:
    :param base_url:
    :param kwargs:
    :return:
    """
    # warnings.warn('flaskz.utils.api_request() has been replaced by flaskz.utils.request()', category=DeprecationWarning)

    success, result = request(url, method=method, url_params=url_params, base_url=base_url, raw_response=raw_response, **kwargs)
    if success:
        return result
    return res_status_codes.api_request_err, result


def request(url, method="GET", url_params=None, base_url="", raw_response=False, **kwargs):
    """
    Request an api.

   .. versionadded:: 1.8.0 - add to replace api_request @2024-05-02

    Example
        # post request
        request('req_url', 'POST', json=payload)
        request({'url': 'req_url', 'method': 'POST'}, json=payload)

        # get request
        request('req_url', headers={'Authorization': 'eyJhbGciOiJIUzUxMiIs......'})

        # base url
        request('req_url', base_url='base_url') # url --> 'base_url/req_url'

        # url_variables
        request('req_url/{id}/', url_variables={'id': 1}) # url --> 'req_url/1/'

        # url_search_params
        request('req_url', url_search_params={'id': 1}) # url --> 'req_url?id=1'

        # http_kwargs
        request('req_url', http_kwargs={ # --> HTTPAdapter parameters
            'pool_connections': 10, 'pool_maxsize': 100, 'max_retries': 10
        })

    :param url:
    :param method:
    :param url_params:
    :param raw_response:
    :param base_url:
    :param kwargs:
    :return:
    """
    _method = method
    if is_dict(url):
        _url = url.get('url')
        if 'method' in url:
            _method = url.get("method")
    else:
        _url = url

    if base_url:
        base_url = base_url.rstrip('/')
        _url = _url.lstrip('/')
        _url = base_url + '/' + _url

    if is_dict(url_params):  # @2023-05-30 update variables(for replace)
        _url = _url.format(**url_params)

    url_variables = kwargs.get('url_variables', None)  # @2023-05-30 add variables(for replace)
    if is_dict(url_variables):
        _url = _url.format(**url_variables)

    url_search_params = kwargs.get('url_search_params', None)  # @2023-05-30 add search_params(for append)
    if url_search_params is not None:
        _url = append_url_search_params(_url, url_search_params)

    _method = _method.strip().upper()

    flaskz_logger.debug('Api request:\n   url={url}\n   method={method}\n   data={data}\n   json={json}'.format(**{
        'url': _url,
        'method': _method,
        'data': kwargs.get('data'),
        'json': kwargs.get('json')
    }))
    try:
        res = _request(method=_method, url=_url, **kwargs)  # @2024-01-16 change, requests.request-->_request
        status_code = res.status_code
        result = res.text
        flaskz_logger.debug('Api request completed:\n   status_code={status_code}\n   result={result}'.format(**{
            'status_code': status_code,
            # 'result': slice_str(result, 60, 10, '\n......\n'),
            'result': textwrap.shorten(result, 1000)  # @2022-05-26:将日志输出由slice_str改为了shorten
        }))
        if kwargs.get('close') is not False:  # @2024-01-09 add
            res.close()
        if raw_response is True:
            return True, res
        return True, result
    except Exception as e:
        result = str(e)
        flaskz_logger.exception('Api request failed:\n' + result)

    return False, result


def forward_request(url, payload=None, raw_response=False, error_code=500, **kwargs):
    """
    Forward the request to other service.

    Example:
        @api_bp.route('/<regex(".*"):path>/', methods=HTTP_METHODS)
        def remote(path):
            remote_res = forward_request(base_url + path)
            res = make_response(remote_res[0], remote_res[1])
            for k, v in remote_res[2]:
                if k not in ['Transfer-Encoding']:
                    res.headers[k] = v
            return res

    :param error_code:
    :param payload:
    :param raw_response:
    :param url: The forward url
    :return:
    """
    req_kwargs = {'url': url}
    _payload = payload or ['method', 'data', 'json', 'headers', 'cookies']
    for item in _payload:
        if item == 'json':  # @2022-05-06: fix request.json -->BadRequest('Content-Type was not 'application/json')
            req_kwargs[item] = flask_request.get_json(force=True, silent=True)
        else:
            req_kwargs[item] = getattr(flask_request, item, None)
    req_kwargs['params'] = flask_request.args  # @2022-06-25 add query string
    req_kwargs.update(kwargs)  # kwargs high priority

    url_params = req_kwargs.get('url_params')
    if url_params is None:  # if url_params is none, append request.view_args
        req_kwargs['url_params'] = flask_request.view_args or {}

    req_kwargs['raw_response'] = True

    success, res = request(**req_kwargs)
    if success is False:
        return res, error_code
    if raw_response is True:
        return res
    return res.text, res.status_code, res.headers.items()


def append_url_search_params(url, params):  # @2022-05-09: add
    """
    Appends specified key/value pair as search parameter.
    Only append the key if its value is None.

    Example:
        append_url_search_params('https://example.com',{'foo':1,'bar':2, 'xx': None}) # 'https://example.com?foo=1&bar=2&xx' # append
        append_url_search_params('https://example.com?foo=1&bar=2',{'baz':3}) # 'https://example.com?foo=1&bar=2&baz=3' # append
        append_url_search_params('https://example.com?foo=1&bar=2',{'bar':3}) # 'https://example.com?foo=1&bar=3' # replace
        append_url_search_params('a/b',{'c':3,'d':None}) # 'a/b?c=3&d'

        append_url_search_params('https://example.com', ['a', 'b', 'c=2']) # 'https://example.com?a&b&c=2'
        append_url_search_params('https://example.com', 'a=1&b=2&c')  # 'https://example.com?a=1&b=2&c'

    :param url:
    :param params:
    :return:

    """
    url_parts = urllib_parse.urlparse(url)
    query = dict(urllib_parse.parse_qsl(url_parts.query))

    kv_params = {}
    k_params = []
    params_type = type(params)
    if params_type is list:
        k_params = params
    elif params_type is str:
        k_params = [params]
    elif params_type is dict:
        for k, v in params.items():
            if v is not None:
                kv_params[k] = v
            else:
                k_params.append(k)
        query.update(kv_params)

    query_string = urllib_parse.urlencode(query)
    if len(k_params) > 0:
        k_str = '&'.join(k_params)
        if query_string:
            if not k_str.startswith('&'):
                k_str = '&' + k_str
            query_string += k_str
        else:
            query_string += k_str

    return url_parts._replace(query=query_string).geturl()


def _request(method, url, **kwargs):
    # requests.request
    # @2024-01-26 add
    with sessions.Session() as session:
        http_kwargs = kwargs.get('http_kwargs', None)
        if http_kwargs:
            adapter = HTTPAdapter(**http_kwargs)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
        return session.request(method=method, url=url, **_get_session_request_kwargs(kwargs))


def _get_session_request_kwargs(kwargs):
    global _session_request_kwargs
    if _session_request_kwargs is None:
        _session_request_kwargs = []
        for key in inspect.signature(Session.request).parameters:
            _session_request_kwargs.append(key)

    req_kwargs = {}
    for key, value in kwargs.items():
        if key in _session_request_kwargs:
            req_kwargs[key] = value
    return req_kwargs
