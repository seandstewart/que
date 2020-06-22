#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from typing import Any, Optional
from collections.abc import Mapping


class SentinelType(type):
    """A metaclass for generating a false-y sentinel value

    Useful when a null (None) value is meaningful.
    """

    def __new__(typ, name):
        return super().__new__(typ, name, (), {})

    def __repr__(cls):
        return f"<{cls.__name__}>"

    @classmethod
    def __bool__(cls):
        return False


Unset = SentinelType("unset")


def dict_filter_factory(exclude: Optional[Any] = ..., astype: bool = False):
    if exclude is ...:
        return dict

    if isinstance(exclude, type) or astype:

        def filter(obj, *, __exclude=exclude):
            items = obj.items() if isinstance(obj, Mapping) else obj
            return {x: y for x, y in items if not isinstance(y, __exclude)}

        return filter

    def filter(obj, *, __exclude=exclude):  # type: ignore
        items = obj.items() if isinstance(obj, Mapping) else obj
        return {x: y for x, y in items if y != exclude}

    return filter


def isnamedtuple(x: Any) -> bool:
    """Test whether an object is a named-tuple.

    Named tuples are essentially extended tuples and instance checks don't work.
    The best thing you can do is just test if they have the special attributes that
    differentiate it from a standard tuple.

    Examples
    ------
    >>> from collections import namedtuple
    >>> from typing import NamedTuple
    >>> class Foo(NamedTuple):
    ...     bar: str
    ...
    >>> isnamedtuple(Foo('bar'))
    True
    >>> Foo = namedtuple('Foo', ['bar'])
    >>> isnamedtuple(Foo('bar'))
    True
    >>> isnamedtuple(tuple())
    False
    """
    return isinstance(x, tuple) and hasattr(x, "_fields") and hasattr(x, "_asdict")
