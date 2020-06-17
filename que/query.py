#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import abc
import dataclasses
import enum
from typing import (
    List,
    Tuple,
    Union,
    Any,
    Dict,
    Mapping,
    Collection,
    Hashable,
    Type,
    NamedTuple,
    Iterator,
    Iterable,
    Optional,
    Sized,
)

from .compat import cached_property
from .util import isnamedtuple, Unset, dict_filter_factory


class SQLSyntaxError(SyntaxError):
    ...


class SQLValueError(ValueError):
    ...


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


SQLOpsT = Union[CmpOps, LogOps, BitOps, MathOps]
ParamStyleT = Union[BasicParamStyle, NumParamStyle, NameParamStyle]
DEFAULT_PARAM_STYLE = NumParamStyle.NUM


class AbstractSQL(abc.ABC):
    @abc.abstractmethod
    def to_sql(self, *args, **kwargs) -> Tuple[str, "Arguments"]:
        ...

    @cached_property
    def as_sql(self) -> Tuple[str, "Arguments"]:
        return self.to_sql()

    @staticmethod
    def get_offset(col: Sized, cur: int = 1) -> int:
        return len(col) + cur


@dataclasses.dataclass(frozen=True)
class Field:
    """A generic Field for a SQL statement.

    A ``Field`` represents the most basic component of a SQL statement. It can be used for identifying
    the fields which you plan to select or modify or the fields which you wish to filter by.
    """

    left: Union[str, Unset] = Unset
    right: Union[Any, Unset] = Unset

    def __post_init__(self):
        if {self.left, self.right} == {Unset, Unset}:
            tname = self.__class__
            raise SQLSyntaxError(f"{tname}.left or {tname}.right must be provided")

    @cached_property
    def fetch_sql(self) -> str:
        """A `Field` as represented in a SQL `SELECT` or `RETURNING` statement."""
        if self.left is not Unset:
            # If we have a `value`, treat it as an alias.
            if self.right:
                return f"{self.left} AS {self.right}"
            return self.left
        return self.right


@dataclasses.dataclass(frozen=True)
class Expression(AbstractSQL):
    """An object representation of a simple SQL expression.

    The ``Filter`` builds upon the :class:`Field` object.
        - The ``Filter.field`` provides the name of the column and the value of the filter.
        - The ``Filter.opcode`` provides the operation (equal-to, less-than, ...).
        - The ``Filter.prefix``  an optional prefix to provide to the parameter naming.
    """

    field: Field
    opcode: CmpOps = CmpOps.EQ
    prefix: str = ""

    def __post_init__(self):
        if self.field.left is Unset:
            raise SQLSyntaxError(
                f"{self.__class__.__name__}.field.name must be provided."
            )

    def to_sql(
        self,
        args: "Arguments" = None,
        style: ParamStyleT = DEFAULT_PARAM_STYLE,
        offset: int = 1,
    ) -> Tuple[str, "Arguments"]:
        """Generate a single filter clause of a SQL Statement.

        Parameters
        ----------
        args : optional
            The mutable, ordered list of arguments.
        style : optional
            The DBAPI 2.0 compliant param-style you wish to use in the generated SQL.

        Returns
        -------
        The SQL fragment, as str
        The :class:`ArgList` which will be passed on to the DB client for secure formatting.
        """
        args = Arguments() if args is None else args
        fmt = style.value
        field = self.field
        if style in NameParamStyle:
            name = f"{self.prefix}{field.left}"
            fmt = fmt.format(name)
            field = dataclasses.replace(field, left=name)
        elif style in NumParamStyle:
            fmt = fmt.format(offset)
        args.append(field)
        return f"{self.field.left} {self.opcode} {fmt}", args


class Fields:
    """A container of SQL Fields with some convenience methods.

    A custom list implementation for housing :class:`Field`.
    """

    def __init__(self, fields: Iterable[Field] = ()):
        """The Constructor.

        Parameters
        ----------
        fields : optional
            A collection of :class:`Field`
        """
        self.fields = (*fields,) if not isinstance(fields, tuple) else fields

    def __eq__(self, other: "Fields"):
        try:
            return self.fields == other.fields
        except AttributeError:
            return super().__eq__(other)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.fields.__repr__()})"

    def __iter__(self):
        yield from self.fields.__iter__()

    def __len__(self):
        return len(self.fields)

    def iter_right_values(self) -> Iterator[Any]:
        for x in self:
            yield x.right

    def iter_left_values(self) -> Iterator[str]:
        for x in self:
            yield x.left

    @cached_property
    def aslist(self) -> List[Any]:
        """Return only a list of ``Field.value``."""
        return [*self.iter_right_values()]

    @cached_property
    def asdict(self) -> Dict[str, Any]:
        """Return a mapping of ``Field.name->Field.value``."""
        return {x.left: x.right for x in self if x.left is not Unset}

    @cached_property
    def left(self) -> Tuple[str, ...]:
        """Return a tuple of ``Field.name``."""
        return (*(self.iter_left_values()),)

    @cached_property
    def right(self) -> Tuple[Any, ...]:
        """Return a tuple of ``Field.value``."""
        return (*(self.iter_right_values()),)


class Arguments:
    """An alias for :class:`FieldList` for mental clarity.

    Also provides a convenience method for outputting your args in the appropriate format
    for the selected style
    """

    def __init__(self, fields: Fields = None):
        self.fields = fields or Fields()

    def __len__(self):
        return len(self.fields)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.fields.__repr__()})"

    def append(self, field: Field):
        self.fields = Fields((*self.fields, field))

    def add(self, arguments: "Arguments") -> "Arguments":
        return Arguments(Fields((*self.fields, *arguments.fields)))

    def for_sql(
        self, style: ParamStyleT = DEFAULT_PARAM_STYLE
    ) -> Union[Dict[str, Any], List[Any]]:
        """Output the list of args in the appropriate format for the param-style.

        Parameters
        ----------
        style :
            The enum selection which matches your param-style.
        """
        if style in NameParamStyle:
            return self.fields.asdict
        return self.fields.aslist


class Expressions(AbstractSQL):
    """A list of SQL Filters which with SQL statement generation.

    A custom list implementation for housing :class:`Filter`.
    """

    def __init__(self, expressions: Iterable[Expression] = ()):
        self.expressions = (
            (*expressions,) if not isinstance(expressions, tuple) else expressions
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.expressions.__repr__()})"

    def __iter__(self):
        yield from self.expressions.__iter__()

    def iter_sql(
        self, args: Arguments, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Iterator[str]:
        for i, fylter in enumerate(self, start=offset):
            sql, args = fylter.to_sql(args, style, offset=i)
            yield sql

    def to_sql(
        self,
        args: Arguments = None,
        style: ParamStyleT = DEFAULT_PARAM_STYLE,
        lead: str = "WHERE",
        offset: int = 1,
    ) -> Tuple[str, Arguments]:
        """Generate the ``WHERE`` clause of a SQL statement.

        Parameters
        ----------
        args : optional
            The list of :class:`Fields` which will serve as arguments for formatting the SQL statement.
        style : defaults :class:`NumParamStyle.NUM`

        Returns
        -------
        The WHERE clause for your SQL statement.
        A list of args to pass on to the DB client when performing the query.
        """
        args = Arguments() if args is None else args
        where = "AND\n  ".join(self.iter_sql(args, style, offset))
        return f"{lead}\n  {where}" if where else "", args


@dataclasses.dataclass(frozen=True)
class BaseSQLStatement(AbstractSQL):
    """A Base-class for simple SQL Statements (Select, Update, Insert, etc)"""

    table: str
    schema: Optional[str] = None

    @property
    def table_name(self) -> str:
        return f"{self.schema}.{self.table}" if self.schema else self.table

    def cte(
        self, statement: "BaseSQLStatement", *, alias: str = None
    ) -> "CommonTableExpression":
        alias = alias or (
            f"{self.table_name}_"
            f"{self.__class__.__name__.lower()}_"
            f"{id(self)}".replace("-", "_")
        )
        return CommonTableExpression(self, statement, alias)


@dataclasses.dataclass(frozen=True)
class CommonTableExpression(AbstractSQL):
    expression: BaseSQLStatement
    statement: BaseSQLStatement
    alias: str

    def to_sql(
        self, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Tuple[str, Arguments]:
        cte, exprargs = self.expression.to_sql(style, offset=offset)
        stmt, stmtargs = self.statement.to_sql(style, self.get_offset(exprargs, offset))
        return f"WITH {self.alias} AS (\n{cte}\n)\n{stmt}", exprargs.add(stmtargs)


class JoinType(str, enum.Enum):
    R = "RIGHT"
    L = "LEFT"
    I = "INNER"  # noqa: E741
    O = "OUTER"  # noqa: E741


@dataclasses.dataclass(frozen=True)
class Join(AbstractSQL):
    table: Union[str, "Select"]
    lkey: str
    rkey: str
    schema: Optional[str] = None
    alias: Optional[str] = None
    how: Optional[JoinType] = None
    filters: Optional[Expressions] = None

    @property
    def table_name(self) -> str:
        return f"{self.schema}.{self.table}" if self.schema else self.table

    def to_sql(self, offset: int = 1) -> str:
        alias = f" AS {self.alias}" if self.alias else ""
        how = self.how.value if self.how else ""
        filters = self.filters.to_sql(lead="AND", offset=offset) if self.filters else ""
        return f"{how} JOIN {self.table_name} {alias}\n  ON {self.lkey}\n  {filters}"

    @cached_property
    def as_sql(self) -> str:
        return self.to_sql()


@dataclasses.dataclass(frozen=True)
class Select(BaseSQLStatement):
    """A simple, single-table SQL SELECT statement.

    As the first line indicates, this does not currently support JOINs.
    """

    filters: Expressions = dataclasses.field(default_factory=Expressions)
    fields: Fields = dataclasses.field(default_factory=Fields)
    joins: Tuple[Join] = dataclasses.field(default_factory=tuple)

    def build_select(self) -> str:
        """Build the SELECT clause of a SQL statement.

        If :attr:`Select.fields` is empty, default to selecting all columns.
        """
        columns = ",\n  ".join(f.fetch_sql for f in self.fields)
        return f"SELECT\n  {columns}\nFROM\n  {self.table_name}"

    def to_sql(
        self, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Tuple[str, Union[List, Dict]]:
        """Generate a valid SQL SELECT statement for a single table.

        Parameters
        --------
        style : defaults :class:`NumParamStyle.NUM`
            The DBAPI 2.0 param-style.

        Returns
        -----
        The generated SQL SELECT statement
        The arguments to pass to the DB client for secure formatting.
        """
        select = self.build_select()
        where, args = self.filters.to_sql(style=style, offset=offset)
        joins = "\n".join(j.as_sql for j in self.joins)
        if joins:
            joins = f"{joins}\n"
        return f"{select}\n{joins}{where}", args.for_sql(style)


class _BaseWriteStatement(BaseSQLStatement):
    fields: Fields
    returns: Optional[Field]

    @cached_property
    def returning(self) -> str:
        """Get the RETURNING clause of write statement, if any is specified.

        Notes
        ----
        While RETURNING is not officially a part of the SQL standard, it's used in enough of the more
        popular SQL implementations available (such as Postgres) to warrant its inclusion as an optional
        parameter.
        """
        return f"RETURNING {self.returns.fetch_sql}" if self.returns else ""


@dataclasses.dataclass(frozen=True)
class Update(_BaseWriteStatement):
    """A simple, single-table SQL UPDATE Statement."""

    filters: Expressions = dataclasses.field(default_factory=Expressions)
    fields: Fields = dataclasses.field(default_factory=Fields)
    joins: Tuple[Join] = dataclasses.field(default_factory=tuple)
    returns: Optional[Field] = None

    def iter_columns(
        self, args: Arguments, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Iterator[str]:
        for i, field in enumerate(self.fields, start=offset):
            stmnt, args = Expression(field, prefix="col").to_sql(args, style, offset=i)
            yield stmnt

    def build_update(
        self, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Tuple[str, Arguments]:
        """Build the SQL UPDATE clause.

        Parameters
        --------
        style : defaults :class:`NumParamStyle.NUM`
            The DBAPI 2.0 param-style.

        Returns
        -----
        The generated UPDATE clause of a SQL statement
        The arguments to pass to the DB client for secure formatting.
        """
        args = Arguments()
        updates = ",\n  ".join(self.iter_columns(args, style, offset=offset))
        return f"UPDATE\n  {self.table_name}\nSET\n  {updates}", args

    def to_sql(
        self, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Tuple[str, Union[List, Dict]]:
        """Build the SQL UPDATE clause.

        Parameters
        --------
        style : defaults :class:`NumParamStyle.NUM`
            The DBAPI 2.0 param-style.

        Returns
        -----
        The generated SQL UPDATE statement
        The arguments to pass to the DB client for secure formatting.
        """
        update, args = self.build_update(style, offset=offset)
        offset = self.get_offset(args, offset)
        where, args = self.filters.to_sql(args, style, offset=offset)
        joins = "\n,  ".join((j.as_sql for j in self.joins))
        returning = self.returning
        return f"{update}\n{joins}\n{where}\n{returning}", args.for_sql(style)


@dataclasses.dataclass(frozen=True)
class Insert(_BaseWriteStatement):
    """A simple, single-table SQL INSERT Statement.

    While the syntax for a SQL INSERT statement is quite simple conceptually, it is arguably the most
    complex to generate (barring JOIN statements). This statement alone is the reason this library was
    implemented, as I'd grown tired of solving the same problem every time an ORM wasn't a viable option.
    """

    fields: Fields = dataclasses.field(default_factory=Fields)
    returns: Field = None

    @staticmethod
    def _iter_fields(fields: Fields, style: ParamStyleT, offset: int = 1) -> str:
        for i, field in enumerate(fields, start=offset):
            # convert the enum to str
            fmt = style.value
            # name the parameter according to the style
            if style in NumParamStyle:
                fmt = fmt.format(i)
            elif style in NameParamStyle:
                fmt = fmt.format(field.left)
            yield fmt

    def _fields_to_sql(
        self, fields: Fields, style: ParamStyleT, offset: int = 1, inject: bool = False,
    ) -> str:
        # Override DBAPI formatting. This is dangerous,
        # but required for columns on insert statements in some clients.
        if inject:
            return f"({', '.join(fields.iter_right_values())})"

        # join the parameters
        stmnts = ",\n  ".join(self._iter_fields(fields, style, offset))
        # return them as a single, SQL-compliant fragment
        return f"({stmnts})" if stmnts else ""

    def build_insert(
        self,
        style: ParamStyleT = DEFAULT_PARAM_STYLE,
        *,
        inject_columns: bool = False,
        offset: int = 1,
    ) -> Tuple[str, Arguments]:
        """Build a SQL INSERT statement.

        We create two new :class:`FieldList` - one for column declaration and one for values declaration.
        We combine them as a single :class:`ArgList` (order is important!).
        We generate the SQL fragments for the INSERT INTO clause and the VALUES clause.
        We check for a RETURNING clause.
        Finally, we join it all together into one SQL statement.

        Parameters
        --------
        style : defaults :class:`NumParamStyle.NUM`
            The DBAPI 2.0 param-style.
        inject_columns: defaults False
            Inject the column names directly, rather than rely on DBAPI formatting.
            This is necessary for some client, such as ``asyncpg``.

        Returns
        -----
        The generated SQL INSERT statement
        The arguments to pass to the DB client for secure formatting.
        """
        columns = Fields((Field(f"col{x.left}", x.left) for x in self.fields))
        colargs = Arguments(columns)
        values = Fields((Field(f"val{x.left}", x.right) for x in self.fields))
        valargs = Arguments(values)
        insert_sql = self._fields_to_sql(
            columns, style, inject=inject_columns, offset=offset
        )
        values_sql = self._fields_to_sql(
            values, style, offset=self.get_offset(colargs, offset)
        )
        returning = self.returning
        return (
            (
                f"INSERT INTO\n  {self.table_name} {insert_sql}\n"
                f"VALUES\n  {values_sql}\n"
                f"{returning}"
            ),
            valargs if inject_columns else colargs.add(valargs),
        )

    def to_sql(
        self,
        style: ParamStyleT = DEFAULT_PARAM_STYLE,
        inject_columns: bool = True,
        offset: int = 1,
    ) -> Tuple[str, Union[List, Dict]]:
        """Build the SQL INSERT statement and format the list of arguments to pass to the DB client.

        Parameters
        --------
        style : defaults :class:`NumParamStyle.NUM`
            The DBAPI 2.0 param-style.
        inject_columns: defaults False
            Inject the column names directly, rather than rely on DBAPI formatting.
            This is necessary for some client, such as ``asyncpg``.

        Returns
        -----
        The generated SQL INSERT statement
        The arguments to pass to the DB client for secure formatting.
        """
        query, args = self.build_insert(
            style, inject_columns=inject_columns, offset=offset
        )
        return query, args.for_sql(style)


@dataclasses.dataclass(frozen=True)
class Delete(_BaseWriteStatement):
    """A simple, single-table SQL DELETE Statement."""

    filters: Expressions = dataclasses.field(default_factory=Expressions)
    joins: Tuple[Join] = dataclasses.field(default_factory=tuple)
    returns: Field = None

    def to_sql(
        self, style: ParamStyleT = DEFAULT_PARAM_STYLE, offset: int = 1
    ) -> Tuple[str, Union[List, Dict]]:
        """Generate a SQL DELETE statement.

        Parameters
        --------
        style : defaults :class:`NumParamStyle.NUM`
            The DBAPI 2.0 param-style.

        Returns
        -----
        The generated SQL DELETE statement
        The arguments to pass to the DB client for secure formatting.
        """
        where, args = self.filters.to_sql(style=style, offset=offset)
        joins = "\n,  ".join(j.as_sql for j in self.joins)
        return (
            f"DELETE FROM\n  {self.table_name}\n{joins}\n{where}\n{self.returning}",
            args.for_sql(style),
        )


SQLStatementT = Union[Select, Insert, Update, Delete]


FieldDataT = Union[Dict, Collection[Tuple[Hashable, Any]], NamedTuple, Type]


def data_to_fields(data: FieldDataT, exclude: Any = Unset) -> Fields:
    """Convert a dataclass, NamedTuple, dict, or array of tuples to a FieldList.

    Parameters
    --------
    data
        Any data-source which you wish to conver to a list of fields.
    exclude
        Any value or type which you wish to exclude
    """
    if data:
        dict_factory = dict_filter_factory(exclude=exclude)
        if dataclasses.is_dataclass(data):
            filtered = dataclasses.asdict(data, dict_factory=dict_factory)
        elif isnamedtuple(data):
            filtered = dict_factory(data._asdict())
        elif isinstance(data, Mapping) or (
            isinstance(data, Collection)
            and all((isinstance(x, Tuple) and len(x) == 2) for x in data)
        ):
            filtered = dict_factory(data)
        else:
            raise SQLValueError(
                "Data must not be empty and be of type dataclass, namedtuple, mapping, "
                f"or collection of tuples whose len is 2. Provided {type(data)}: {data}"
            )

        return Fields((Field(x, y) for x, y in filtered.items()))
