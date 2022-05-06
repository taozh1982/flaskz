__all__ = ['typed_property', 'init_properties']


def typed_property(name, expected_type):
    """
    Example 1:
    class Person:
        name = typed_property('name', str)
        age = typed_property('age', int)

    Example 2:
    String = partial(typed_property, expected_type=str)
    Integer = partial(typed_property, expected_type=int)
    class Person:
        name = String('name')
        age = Integer('age')

    :param name:
    :param expected_type:
    :return:
    """
    storage_name = '_' + name

    @property
    def prop(self):
        return getattr(self, storage_name)

    @prop.setter
    def prop(self, value):
        if not isinstance(value, expected_type):
            raise TypeError('{} must be a {}'.format(name, expected_type))
        setattr(self, storage_name, value)

    return prop


def init_properties(self, extra_kwargs, *args, **kwargs):
    """
    class A:
        _fields = ['a', 'b', 'c']

        def __init__(self, *args, **kwargs):
            init_property(self, False, *args, **kwargs)


    class B:
        _fields = ['a', 'b', 'c']

        def __init__(self, *args, **kwargs):
            init_property(self, True, *args, **kwargs)  # extended keyword arguments


    print(A(1, 2, 3))
    print(A(1, 2, c=3))
    print(A(1, b=2, c=3))
    # print(A(1, 2, 3, e=4))  # TypeError: A got an unexpected keyword argument e
    # print(A(1, 2, 3, 4))  # TypeError: A takes 3 positional arguments but 4 were given
    # print(A(1, 2, 3, a=4))  # TypeError: A got an unexpected keyword argument a

    print(B(1, 2, 3))
    print(B(1, 2, c=3))
    print(B(1, b=2, c=3))
    print(B(1, 2, 3, e=4))
    # print(B(1, 2, 3, 4))  # TypeError: B takes 3 positional arguments but 4 were given
    # print(B(1, 2, 3, a=4))  # TypeError: B got an unexpected keyword argument a
    """
    _fields = getattr(self, '_fields', [])
    filed_len = len(_fields)
    args_len = len(args)
    cls_name = self.__class__.__name__
    if args_len > filed_len:
        raise TypeError(cls_name + ' takes {} positional arguments but {} were given'.format(filed_len, args_len))

    for name, value in zip(_fields, args):
        setattr(self, name, value)

    for name in self._fields[args_len:]:
        setattr(self, name, kwargs.pop(name))

    if extra_kwargs is True:
        extra_args = kwargs.keys() - self._fields
        for name in extra_args:
            setattr(self, name, kwargs.pop(name))

    if kwargs:
        raise TypeError(cls_name + ' got an unexpected keyword argument {}'.format(','.join(kwargs)))

    return self
