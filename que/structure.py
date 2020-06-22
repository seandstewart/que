#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import abc
import dataclasses
import enum
from itertools import chain
from typing import (
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
    cast,
)

from .compat import cached_property
from .keywords import CmpOps, Clause, LogOps
from .style import ParamStyleT, NumParamStyle, NameParamStyle, default_style
from .util import isnamedtuple, dict_filter_factory


class SQLSyntaxError(SyntaxError):
    ...


class SQLValueError(ValueError):
    ...


class AbstractSQL(abc.ABC):
    @abc.abstractmethod
    def to_sql(
        self, style: ParamStyleT = None, offset: int = 1, **kwargs
    ) -> Tuple[str, "Arguments"]:
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

    left: str = ...  # type: ignore
    right: Any = ...  # type: ignore

    def __post_init__(self):
        if {self.left, self.right} == {..., ...}:
            tname = self.__class__
            raise SQLSyntaxError(f"{tname}.left or {tname}.right must be provided")

    @cached_property
    def fetch_sql(self) -> str:
        """A `Field` as represented in a SQL `SELECT` or `RETURNING` statement."""
        if self.left is not ...:
            # If we have a `value`, treat it as an alias.
            if self.right is not ...:
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
        if self.field.left is ...:
            raise SQLSyntaxError(
                f"{self.__class__.__name__}.field.name must be provided."
            )

    def to_sql(  # type: ignore
        self, style: ParamStyleT = None, offset: int = 1, **_
    ) -> Tuple[Field, str]:
        """Generate a single filter clause of a SQL Statement.

        Parameters
        ----------
        style : optional
            The DBAPI 2.0 compliant param-style you wish to use in the generated SQL.


        Returns
        -------
        The SQL fragment, as str
        The :class:`ArgList` which will be passed on to the DB client for secure formatting.
        """
        style = style or default_style()
        fmt = style.value
        field = self.field
        if style in NameParamStyle:
            name = f"{self.prefix}{field.left}"
            fmt = fmt.format(name)
            field = dataclasses.replace(field, left=name)
        elif style in NumParamStyle:
            fmt = fmt.format(offset)
        return field, f"{self.field.left} {self.opcode} {fmt}"


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

    def _clear_cache(self):
        for cache in ("mapping", "left", "right"):
            if hasattr(self, cache):
                delattr(self, cache)

    def add(self, fields: "Fields") -> "Fields":
        return Fields(chain(self.fields, fields.fields))

    __add__ = add

    def iadd(self, fields: "Fields") -> "Fields":
        self.fields += fields.fields
        self._clear_cache()
        return self

    __iadd__ = iadd

    def __eq__(self, o):
        if isinstance(o, Fields):
            return self.fields == o.fields
        return super().__eq__(o)

    def __hash__(self):
        return self.fields.__hash__()

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
    def mapping(self) -> Dict[str, Any]:
        """Return a mapping of ``Field.name->Field.value``."""
        return {x.left: x.right for x in self if x.left is not ...}

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
        return Arguments(self.fields + arguments.fields)

    __add__ = add

    def iadd(self, arguments: "Arguments") -> "Arguments":
        self.fields += arguments.fields
        return self

    __iadd__ = iadd

    def __eq__(self, o):
        if isinstance(o, Arguments):
            return self.fields == o.fields
        return super().__eq__(o)

    def for_sql(
        self, style: ParamStyleT = None
    ) -> Union[Dict[str, Any], Iterable[Any]]:
        """Output the list of args in the appropriate format for the param-style.

        Parameters
        ----------
        style :
            The enum selection which matches your param-style.
        """
        style = style or default_style()
        if style in NameParamStyle:
            return self.fields.mapping
        return self.fields.right


class Expressions(AbstractSQL):
    """A list of SQL Filters which with SQL statement generation.

    A custom list implementation for housing :class:`Filter`.
    """

    def __init__(self, expressions: Iterable[Expression] = ()):
        self.expressions: Tuple[Expression, ...] = (
            (*expressions,) if not isinstance(expressions, tuple) else expressions
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.expressions.__repr__()})"

    def __iter__(self):
        yield from self.expressions.__iter__()

    def iter_sql(
        self, style: ParamStyleT = None, offset: int = 1
    ) -> Iterator[Tuple[Field, str]]:
        for i, expression in enumerate(self, start=offset):
            yield expression.to_sql(style, offset=i)

    def fields_to_sql(
        self, style: ParamStyleT = None, offset: int = 1
    ) -> Mapping[Field, str]:
        return dict(self.iter_sql(style=style, offset=offset))

    def to_sql(  # type: ignore
        self,
        style: ParamStyleT = None,
        offset: int = 1,
        *,
        lead: Union[Clause, LogOps] = Clause.WHR,
    ) -> Tuple[str, Arguments]:
        """Generate the ``WHERE`` clause of a SQL statement.

        Parameters
        ----------
        style
            defaults :class:`NumParamStyle.NUM`
        offset
            The offset for the parameter counter (only needed for number-based params).
            defaults 1
        lead
            The leading keyword for the statement block. defaults "WHERE".

        Returns
        -------
        The WHERE clause for your SQL statement.
        A list of args to pass on to the DB client when performing the query.
        """
        fields_to_sql = self.fields_to_sql(style=style, offset=offset)
        where = f"{LogOps.AND}\n  ".join(fields_to_sql.values())
        args = Arguments(Fields(fields_to_sql.keys()))
        return f"{lead}\n  {where}" if where else "", args


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
    def table_name(self) -> Union[str, "Select"]:
        return f"{self.schema}.{self.table}" if self.schema else self.table

    def to_sql(
        self, style: ParamStyleT = None, offset: int = 1, **_
    ) -> Tuple[str, Arguments]:
        style = style or default_style()
        alias = f" {Clause.AS} {self.alias}" if self.alias else ""
        how = self.how.value if self.how else ""
        table = self.table_name
        args = Arguments()
        if isinstance(table, Select):
            table, selargs = table.to_sql(style, offset, render_args=False)
            args = cast(Arguments, selargs)

        filters, filtargs = (
            self.filters.to_sql(lead=LogOps.AND, offset=offset,)
            if self.filters
            else ("", Arguments())
        )
        args += filtargs
        return (
            f"{how} {Clause.JOIN} {self.table_name} {alias}\n  {Clause.ON} {self.lkey}\n  {filters}",
            args,
        )

    @cached_property
    def as_sql(self) -> str:
        return self.to_sql()[0]


@dataclasses.dataclass(frozen=True)
class CommonTableExpression(AbstractSQL):
    expression: "BaseSQLStatement"
    statement: "BaseSQLStatement"
    alias: str

    def to_sql(
        self, style: ParamStyleT = None, offset: int = 1, **_
    ) -> Tuple[str, Arguments]:
        style = style or default_style()
        cte, exprargs = self.expression.to_sql(style, offset=offset)
        stmt, stmtargs = self.statement.to_sql(style, self.get_offset(exprargs, offset))
        exprargs += stmtargs
        return f"{Clause.WITH} {self.alias} {Clause.AS} (\n{cte}\n)\n{stmt}", exprargs


@dataclasses.dataclass(frozen=True)  # type: ignore
class BaseSQLStatement(AbstractSQL):
    """A Base-class for simple SQL Statements (Select, Update, Insert, etc)"""

    table: str
    schema: Optional[str] = None
    filters: Expressions = dataclasses.field(default_factory=Expressions)
    fields: Fields = dataclasses.field(default_factory=Fields)
    joins: Tuple[Join, ...] = ()

    @property
    def table_name(self) -> str:
        return f"{self.schema}.{self.table}" if self.schema else self.table

    def build_joins(self, style: ParamStyleT, offset: int, args: Arguments) -> str:
        joins = ""
        for j in self.joins:
            stmt, jargs = j.to_sql(style=style, offset=offset)
            joins = f"{joins}{stmt}\n"
            args += jargs
            offset += len(jargs)

        return joins

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
class Select(BaseSQLStatement):
    """A simple, single-table SQL SELECT statement.

    As the first line indicates, this does not currently support JOINs.
    """

    def build_select(self) -> str:
        """Build the SELECT clause of a SQL statement.

        If :attr:`Select.fields` is empty, default to selecting all columns.
        """
        columns = ",\n  ".join(f.fetch_sql for f in self.fields)
        return f"{Clause.SEL}\n  {columns}\n{Clause.FROM}\n  {self.table_name}"

    def to_sql(  # type: ignore
        self, style: ParamStyleT = None, offset: int = 1, **_,
    ) -> Tuple[str, Arguments]:
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
        style = style or default_style()
        select = self.build_select()
        where, args = self.filters.to_sql(style=style, offset=offset)
        offset = self.get_offset(args, offset)
        joins = self.build_joins(style=style, offset=offset, args=args)
        return f"{select}\n{joins}{where}", args


@dataclasses.dataclass(frozen=True)  # type: ignore
class _BaseWriteStatement(BaseSQLStatement):
    returns: Optional[Field] = None

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

    def iter_columns(
        self, style: ParamStyleT = None, offset: int = 1
    ) -> Iterator[Tuple[Field, str]]:
        for i, field in enumerate(self.fields, start=offset):
            yield Expression(field, prefix="col").to_sql(style, offset=i)

    def build_update(
        self, style: ParamStyleT = None, offset: int = 1
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
        fields_to_sql = dict(self.iter_columns(style=style, offset=offset))
        updates = ",\n  ".join(fields_to_sql.values())
        return (
            f"{Clause.UPD}\n  {self.table_name}\n{Clause.SET}\n  {updates}",
            Arguments(Fields(fields_to_sql.keys())),
        )

    def to_sql(
        self, style: ParamStyleT = None, offset: int = 1, **_
    ) -> Tuple[str, Arguments]:
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
        style = style or default_style()
        update, args = self.build_update(style, offset=offset)
        offset = self.get_offset(args, offset)
        where, whargs = self.filters.to_sql(style, offset=offset)
        args += whargs
        offset = self.get_offset(args, offset)
        joins = self.build_joins(style=style, offset=offset, args=args)
        returning = self.returning
        return f"{update}\n{joins}\n{where}\n{returning}", args


@dataclasses.dataclass(frozen=True)
class Insert(_BaseWriteStatement):
    """A simple, single-table SQL INSERT Statement.

    While the syntax for a SQL INSERT statement is quite simple conceptually, it is arguably the most
    complex to generate (barring JOIN statements). This statement alone is the reason this library was
    implemented, as I'd grown tired of solving the same problem every time an ORM wasn't a viable option.
    """

    @staticmethod
    def _iter_fields(
        fields: Fields, style: ParamStyleT, offset: int = 1
    ) -> Iterator[str]:
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
        self, style: ParamStyleT, offset: int, *, inject_columns: bool = True,
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
        values = Fields((Field(f"val{x.left}", x.right) for x in self.fields))
        insert_sql = self._fields_to_sql(
            columns, style, inject=inject_columns, offset=offset
        )
        # Only move the offset if we're NOT injecting columns.
        if not inject_columns:
            offset = self.get_offset(columns, offset)
        values_sql = self._fields_to_sql(values, style, offset=offset)
        returning = self.returning
        retvals = values
        # Combine the columns & values if we're not injecting columns
        if not inject_columns:
            retvals = columns
            retvals += values
        sql = (
            f"{Clause.INS} {Clause.INTO}\n  {self.table_name} {insert_sql}\n"
            f"{Clause.VALS}\n  {values_sql}\n"
            f"{returning}"
        )
        return sql, Arguments(retvals)

    def to_sql(  # type: ignore
        self,
        style: ParamStyleT = None,
        offset: int = 1,
        *,
        inject_columns: bool = True,
    ) -> Tuple[str, Arguments]:
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
        style = style or default_style()
        query, args = self.build_insert(
            style, inject_columns=inject_columns, offset=offset
        )
        return query, args


@dataclasses.dataclass(frozen=True)
class Delete(_BaseWriteStatement):
    """A simple, single-table SQL DELETE Statement."""

    def to_sql(
        self, style: ParamStyleT = None, offset: int = 1, **_
    ) -> Tuple[str, Arguments]:
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
        style = default_style()
        where, args = self.filters.to_sql(style=style, offset=offset)
        offset = self.get_offset(args, offset)
        joins = self.build_joins(style=style, offset=offset, args=args)
        sql = f"{Clause.DEL} {Clause.FROM} {self.table_name}\n{joins}\n{where}\n{self.returning}"
        return sql, args


SQLStatementT = Union[Select, Insert, Update, Delete]


FieldDataT = Union[Dict, Collection[Tuple[Hashable, Any]], NamedTuple, Type]


def data_to_fields(data: FieldDataT, exclude: Any = ...) -> Fields:
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
            filtered = dict_factory(data._asdict())  # type: ignore
        elif isinstance(data, Mapping) or (
            isinstance(data, Collection)
            and all((isinstance(x, Collection) and len(x) == 2) for x in data)
        ):
            filtered = dict_factory(data)
        else:
            raise SQLValueError(
                "Data must be of type dataclass, namedtuple, mapping, "
                f"or collection of tuples whose len is 2. Provided {type(data)}: {data}"
            )

        return Fields((Field(x, y) for x, y in filtered.items()))

    return Fields(())
