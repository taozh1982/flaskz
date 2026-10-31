import re


def route(app, rule, methods=None, endpoint=None):
    """
    Register a route for Flask or FastAPI.

    :param app: Flask, Blueprint, FastAPI or APIRouter
    :param rule: URL rule
    :param methods: HTTP methods
    :param endpoint: Endpoint name
    """
    methods = methods or ['GET']

    def decorator(func):
        if callable(getattr(app, 'add_api_route', None)):
            # FastAPI: convert Flask URL parameters
            # <did> -> {did}
            # <int:did> -> {did:int}
            app.add_api_route(_to_fastapi_rule(rule), endpoint=func, methods=methods, name=endpoint)
        else:
            # Flask / Blueprint
            app.route(_to_flask_rule(rule), methods=methods, endpoint=endpoint)(func)
        return func

    return decorator


def gen_route_rule(rule, *, strict_slash=True, did_suffix=None, rule_suffix=None):
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


def _to_fastapi_rule(rule):
    """
    Convert Flask-style URL parameters to FastAPI format.
    not support :'/devices/<any(active,inactive):status>'类型
    """
    converter_map = {
        'string': 'str',
        'int': 'int',
        'float': 'float',
        'path': 'path',
        'uuid': 'uuid'
    }

    def replace(match):
        converter, name = match.groups()

        if converter is None:
            return '{' + name + '}'

        converter = converter_map.get(converter)
        if converter is None:
            raise ValueError(f'Unsupported route converter: {match.group(0)}')

        return '{' + name + ':' + converter + '}'

    return re.sub(r'<(?:(\w+):)?(\w+)>', replace, rule)


def _to_flask_rule(rule):
    """Convert FastAPI-style URL parameters to Flask format."""
    converter_map = {
        'str': 'string',
        'int': 'int',
        'float': 'float',
        'path': 'path',
        'uuid': 'uuid'
    }

    def replace(match):
        name, converter = match.groups()

        if converter is None:
            return '<' + name + '>'

        converter = converter_map.get(converter)
        if converter is None:
            raise ValueError(f'Unsupported route converter: {match.group(0)}')

        return '<' + converter + ':' + name + '>'

    return re.sub(r'\{(\w+)(?::(\w+))?\}', replace, rule)
