from __future__ import unicode_literals, print_function
__metaclass__ = type


def as_iterable(vs):
    """
    >>> list(as_iterable(None))
    []
    >>> list(as_iterable([1]))
    [1]
    >>> list(as_iterable(1))
    [1]
    """
    if vs is None:
        return
    if isinstance(vs, list):
        for v in vs:
            yield v
    else:
        yield vs
