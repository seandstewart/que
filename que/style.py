import enum
from typing import Union


class BasicParamStyle(str, enum.Enum):
    """Simple DBAPI 2.0 compliant param styles."""

    QM = "?"
    FM = "%s"


class NumParamStyle(str, enum.Enum):
    """Numbered DBAPI 2.0 compliant param styles."""

    NUM = ":{}"
    DOL = "${}"


class NameParamStyle(str, enum.Enum):
    """Named DBAPI 2.0 compliant param styles"""

    NAME = ":{}"
    PYFM = "%({})s"


class DefaultStyle:

    DEFAULT: "ParamStyleT" = NumParamStyle.NUM

    def __repr__(self):
        return self.DEFAULT.__repr__()

    def __str__(self):
        return self.DEFAULT.__str__()

    def __eq__(self, other):
        return self.DEFAULT.__eq__(other)

    def __hash__(self):
        return self.DEFAULT.__hash__()

    @property
    def value(self):
        return self.DEFAULT.value


ParamStyleT = Union[BasicParamStyle, NumParamStyle, NameParamStyle, DefaultStyle]
DEFAULT_PARAM_STYLE: DefaultStyle = DefaultStyle()


def default_style(style: ParamStyleT = None) -> ParamStyleT:
    if style:
        DEFAULT_PARAM_STYLE.DEFAULT = style
    return DEFAULT_PARAM_STYLE.DEFAULT
