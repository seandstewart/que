#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from functools import partial
from typing import Dict, Any, Sequence, Optional, Union, Tuple, Hashable


class Nothing:
    """A placeholder to indicate no value has been given for a parameter"""

    pass


class DictFactory:
    """A factory for producing a dictionary with optional exclusions

    Examples
    --------
    >>> dict_factory = DictFactory(exclude=None)
    >>> dict_factory({'x': 0, 'y': None}, exclude=None)
    {'x': 0}
    """

    def __new__(cls, exclude: Optional[Any] = Nothing) -> "factory":
        return partial(cls.factory, exclude=exclude)

    @staticmethod
    def factory(
        obj: Union[Dict, Sequence[Tuple[Hashable, Any]]],
        exclude: Optional[Any] = Nothing,
    ) -> Dict:
        """Produce a dictionary from a supplied object. Optionally exclude a specific value or type from the output

        Examples
        --------
        >>> DictFactory.factory({'x': 0, 'y': None}, exclude=None)
        {'x': 0}
        >>> DictFactory.factory([('x', 0), ('y', None)], exclude=int)
        {'y': None}
        """
        if isinstance(obj, Dict) and exclude is Nothing:
            # Don't do anything if we don't have to
            return obj
        # coerce Dict to simplify transformation
        obj = obj.items() if isinstance(obj, Dict) else obj

        def _cmp(val):
            """Set the comparator"""
            return (
                isinstance(val, exclude)
                if isinstance(exclude, type)
                else val == exclude
            )

        return dict(((x, y) for x, y in obj if _cmp(y) is False))


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
