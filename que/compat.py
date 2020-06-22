# flake8: noqa
try:
    from functools import cached_property  # type: ignore
except ImportError:
    from cached_property import cached_property
