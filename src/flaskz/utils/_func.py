__all__ = ['get_list_args']


def get_list_args(params, args):  # @2022-05-11: add
    """
    Returns a single new list combining keys and args

    def xxx(names, *args):
        print(get_list_args(names, args))

    xxx('a', ['b', 'c'])    -->['a', 'b', 'c']
    xxx('a', 'b', 'c')      -->['a', 'b', 'c']
    xxx(['a', 'b'], 'c')    -->['a', 'b', 'c']
    xxx(['a', 'b', 'c'])    -->['a', 'b', 'c']

    :param params:
    :param args:
    :return:
    """
    try:
        iter(params)
        if isinstance(params, (bytes, str)):
            params = [params]
        else:
            params = list(params)
    except TypeError:
        params = [params]
    if args and len(args) > 0:
        if isinstance(args[0], (tuple, list)):
            params.extend(*args)
        else:
            params.extend(args)
    return params
