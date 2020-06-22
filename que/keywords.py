import enum
from typing import Union


class MathOps(str, enum.Enum):
    """Common SQL arithmetic operations."""

    ADD = "+"
    IADD = "+="
    SUB = "-"
    ISUB = "-="
    MUL = "*"
    IMUL = "*="
    DIV = "/"
    IDIV = "/="
    MOD = "%"
    IMOD = "%="


class BitOps(str, enum.Enum):
    """SQL Bitwise operations."""

    AND = "&"
    IAND = "&="
    OR = "|"
    IOR = "|*="
    XOR = "^"
    IXOR = "^-="


class LogOps(str, enum.Enum):
    """Common SQL Logical Operations."""

    ALL = "ALL"
    AND = "AND"
    ANY = "ANY"
    BET = "BETWEEN"
    EX = "EXISTS"
    IN = "IN"
    ILI = "ILIKE"
    LI = "LIKE"
    NOT = "NOT"
    OR = "OR"
    RE = "REGEXP"


class CmpOps(str, enum.Enum):
    """Common SQL Comparison operations."""

    EQ = "="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    NE = "<>"


class Clause(str, enum.Enum):
    """Common SQL Clause keywords."""

    AS = "AS"
    CONF = "CONFLICT"
    DEL = "DELETE"
    DO = "DO"
    FROM = "FROM"
    INS = "INSERT"
    INTO = "INTO"
    JOIN = "JOIN"
    ON = "ON"
    RET = "RETURNING"
    SEL = "SELECT"
    SET = "SET"
    UPD = "UPDATE"
    VALS = "VALUES"
    WHR = "WHERE"
    WITH = "WITH"


SQLOpsT = Union[CmpOps, LogOps, BitOps, MathOps]
