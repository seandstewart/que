#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import dataclasses
import enum
from typing import (
    List,
    Tuple,
    Union,
    NewType,
    Any,
    Dict,
    Mapping,
    Collection,
    Hashable,
    Type,
    NamedTuple,
)
from collections import UserList

from .util import DictFactory, isnamedtuple, Nothing


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


ParamStyleType = NewType(
    "ParamStyleType", Union[BasicParamStyle, NumParamStyle, NameParamStyle]
)
DEFAULT_PARAM_STYLE = NumParamStyle.NUM


@dataclasses.dataclass
class Field:
    """A generic Field for a SQL statement.

    A ``Field`` represents the most basic component of a SQL statement. It can be used for identifying
    the fields which you plan to select or modify or the fields which you wish to filter by.
    """

    name: str = None
    value: Any = None

    def __post_init__(self):
        try:
            assert (
                self.name or self.value
            ), f"{type(self).__name__}.name or {type(self).__name__}.value must be provided"
        except AssertionError as err:
            raise TypeError(err)

    def for_fetch(self) -> str:
        """Generate valid SQL for a ``Field`` if it is being used in a SELECT or RETURNING statement."""
        return (
            f"{self.name} AS {self.value}"
            if (self.value and self.name)
            else (self.name or self.value)
        )


@dataclasses.dataclass
class Filter:
    """An object representation of a simple SQL filter.

    The ``Filter`` builds upon the :class:`Field` object.
        - The ``Filter.field`` provides the name of the column and the value of the filter.
        - The ``Filter.opcode`` provides the operation (equal-to, less-than, ...).
        - The ``Filter.prefix``  an optional prefix to provide to the parameter naming.
    """

    field: Field
    opcode: CmpOps = CmpOps.EQ
    prefix: str = ""

    def __post_init__(self):
        try:
            assert (
                self.field.name and self.field.value is not None
            ), f"{type(self).__name__}.field must have name and value."
        except AssertionError as err:
            raise TypeError(err)

    def to_sql(
        self, args: "ArgList" = None, style: ParamStyleType = DEFAULT_PARAM_STYLE
    ) -> Tuple[str, "ArgList"]:
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
        args = args or ArgList()
        args.append(self.field)
        fmt = f"{style}"
        if style in NameParamStyle:
            fmt = fmt.format(f"{self.prefix}{self.field.name}")
        elif style in NumParamStyle:
            fmt = fmt.format(len(args))
        return f"{self.field.name} {self.opcode} {fmt}", args


class FieldList(UserList):
    """A list of SQL Fields with some convenience methods.

    A custom list implementation for housing :class:`Field`.
    """

    def __init__(self, initlist: Collection[Field] = None):
        """The Constructor.

        Parameters
        ----------
        initlist : optional
            A collection of :class:`Field`
        """
        initlist = initlist or []
        super().__init__(initlist)

    def __repr__(self):
        return f"{type(self).__name__}([{', '.join(str(x) for x in self)}])"

    def aslist(self) -> List[Any]:
        """Return only a list of ``Field.value``."""
        return list(self.values())

    def asdict(self) -> Dict[str, Any]:
        """Return a mapping of ``Field.name->Field.value``."""
        return {x.name: x.value for x in self if x.name is not None}

    def fields(self) -> Tuple[str, ...]:
        """Return a tuple of ``Field.name``."""
        return tuple(x.name for x in self if x.name is not None)

    def values(self) -> Tuple[Any, ...]:
        """Return a tuple of ``Field.value``."""
        return tuple(x.value for x in self)

    def append(self, item: Field):
        """Append a :class:`Field` to the list.

        Raises
        -----
        TypeError
            If the item sent to be appended is not a :class:`Field`
        """
        if not isinstance(item, Field):
            raise TypeError(f"{type(self).__name__} requires type Field.")
        super().append(item)


class ArgList(FieldList):
    """An alias for :class:`FieldList` for mental clarity.

    Also provides a convenience method for outputting your args in the appropriate format
    for the selected style
    """

    def for_sql(
        self, style: ParamStyleType = DEFAULT_PARAM_STYLE
    ) -> Union[Dict[str, Any], List[Any]]:
        """Output the list of args in the appropriate format for the param-style.

        Parameters
        ----------
        style :
            The enum selection which matches your param-style.
        """
        if style in NameParamStyle:
            return self.asdict()
        return self.aslist()


class FilterList(UserList):
    """A list of SQL Filters which with SQL statement generation.

    A custom list implementation for housing :class:`Filter`.
    """

    def __init__(self, initlist: Collection[Filter] = None):
        initlist = initlist or []
        super().__init__(initlist)

    def __repr__(self):
        return f"{type(self).__name__}([{', '.join(str(x) for x in self)}])"

    def append(self, item: Filter):
        """Append a :class:`Filter` to the list.

        Raises
        -----
        TypeError
            If the item sent to be appended is not a :class:`Filter`
        """
        if not isinstance(item, Filter):
            raise TypeError(f"{type(self).__name__} requires type Filter.")
        super().append(item)

    def to_sql(
        self, args: ArgList = None, style: ParamStyleType = DEFAULT_PARAM_STYLE
    ) -> Tuple[str, ArgList]:
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
        args = args or ArgList()
        where = []
        for fylter in self:
            sql, args = fylter.to_sql(args, style)
            where.append(sql)
        where = "AND\n  ".join(where)

        return f"WHERE\n  {where}" if where else "", args


@dataclasses.dataclass
class BaseSQLStatement:
    """A Base-class for simple SQL Statements (Select, Update, Insert, etc)"""

    def __post_init__(self):
        if hasattr(self, "fields") and not isinstance(self.fields, FieldList):
            self.fields = FieldList(self.fields)
        if hasattr(self, "filters") and not isinstance(self.filters, FilterList):
            self.filters = FilterList(self.filters)

    @property
    def table_name(self) -> str:
        return f"{self.schema}.{self.table}" if self.schema else self.table

    def to_sql(self) -> Tuple[str, Union[List, Dict]]:
        raise NotImplementedError


@dataclasses.dataclass
class Select(BaseSQLStatement):
    """A simple, single-table SQL SELECT statement.

    As the first line indicates, this does not currently support JOINs.
    """

    table: str
    schema: str = None
    filters: FilterList = dataclasses.field(default_factory=FilterList)
    fields: FieldList = dataclasses.field(default_factory=FieldList)

    def build_select(self) -> str:
        """Build the SELECT clause of a SQL statement.

        If :attr:`Select.fields` is empty, default to selecting all columns.
        """
        columns = []
        for field in self.fields:
            columns.append(field.for_fetch())
        columns = ",\n  ".join(columns) if columns else "*"

        return f"SELECT\n  {columns}\nFROM\n  {self.table_name}"

    def to_sql(
        self, style: ParamStyleType = DEFAULT_PARAM_STYLE
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
        where, args = self.filters.to_sql(style=style)
        return f"{select}\n{where}", args.for_sql(style)


class _BaseWriteStatement(BaseSQLStatement):
    def get_returning(self) -> str:
        """Get the RETURNING clause of write statement, if any is specified.

        Notes
        ----
        While RETURNING is not officially a part of the SQL standard, it's used in enough of the more
        popular SQL implementations available (such as Postgres) to warrant its inclusion as an optional
        parameter.
        """
        return f"RETURNING {self.returns.for_fetch()}" if self.returns else ""

    def __post_init__(self):
        super().__post_init__()
        try:
            columns = self.fields.fields()
            values = self.fields.values()
            assert (
                columns and values and len(columns) == len(values)
            ), f"{type(self).__name__}.fields must all have a name and value."
        except AssertionError as err:
            raise TypeError(err)


@dataclasses.dataclass
class Update(_BaseWriteStatement):
    """A simple, single-table SQL UPDATE Statement."""

    table: str
    schema: str = None
    filters: FilterList = dataclasses.field(default_factory=FilterList)
    fields: FieldList = dataclasses.field(default_factory=FieldList)
    returns: Field = None

    def build_update(
        self, style: ParamStyleType = DEFAULT_PARAM_STYLE
    ) -> Tuple[str, ArgList]:
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
        updates = []
        args = ArgList()
        for field in self.fields:
            stmt, args = Filter(field, prefix="col").to_sql(args, style)
            updates.append(stmt)
        updates = ",\n  ".join(updates)
        return f"UPDATE\n  {self.table_name}\nSET\n  {updates}", args

    def to_sql(
        self, style: ParamStyleType = DEFAULT_PARAM_STYLE
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
        update, args = self.build_update(style)
        where, args = self.filters.to_sql(args, style)
        returning = self.get_returning()
        return f"{update}\n{where}\n{returning}", args.for_sql(style)


@dataclasses.dataclass
class Insert(_BaseWriteStatement):
    """A simple, single-table SQL INSERT Statement.

    While the syntax for a SQL INSERT statement is quite simple conceptually, it is arguably the most
    complex to generate (barring JOIN statements). This statement alone is the reason this library was
    implemented, as I'd grown tired of solving the same problem every time an ORM wasn't a viable option.
    """

    table: str
    schema: str = None
    fields: FieldList = dataclasses.field(default_factory=FieldList)
    returns: Field = None

    @staticmethod
    def _fields_to_sql(
        fields: FieldList, style: ParamStyleType, args: ArgList, inject: bool = False
    ) -> str:
        # Override DBAPI formatting. This is dangerous, but required for columns on insert statements in some clients.
        if inject:
            return f"({', '.join(fields.values())})"

        stmnts = []
        for field in fields:
            # convert the enum to str
            fmt = f"{style}"
            # name the parameter according to the style
            if style in NumParamStyle:
                fmt = fmt.format(args.index(field) + 1)
            elif style in NameParamStyle:
                fmt = fmt.format(field.name)
            # append the parameter to the list
            stmnts.append(fmt)
        # join the parameters
        stmnts = ",\n  ".join(stmnts)
        # return them as a single, SQL-compliant fragment
        return f"({stmnts})" if stmnts else ""

    def build_insert(
        self,
        style: ParamStyleType = DEFAULT_PARAM_STYLE,
        *,
        inject_columns: bool = False,
    ) -> Tuple[str, ArgList]:
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
        columns = FieldList([Field(f"col{x.name}", x.name) for x in self.fields])
        values = FieldList([Field(f"val{x.name}", x.value) for x in self.fields])
        args = ArgList(values) if inject_columns else ArgList(columns + values)
        insert_sql = self._fields_to_sql(columns, style, args, inject=inject_columns)
        values_sql = self._fields_to_sql(values, style, args)
        returning = self.get_returning()
        return (
            (
                f"INSERT INTO\n  {self.table_name} {insert_sql}\n"
                f"VALUES\n  {values_sql}\n"
                f"{returning}"
            ),
            args,
        )

    def to_sql(
        self, style: ParamStyleType = DEFAULT_PARAM_STYLE, inject_columns: bool = False
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
        query, args = self.build_insert(style, inject_columns=inject_columns)
        return query, args.for_sql(style)


@dataclasses.dataclass
class Delete(BaseSQLStatement):
    """A simple, single-table SQL DELETE Statement."""

    table: str
    schema: str = None
    filters: FilterList = dataclasses.field(default_factory=FilterList)
    returns: Field = None

    def get_returning(self) -> str:
        return f"RETURNING {self.returns.for_fetch()}" if self.returns else ""

    def to_sql(
        self, style: ParamStyleType = DEFAULT_PARAM_STYLE
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
        where, args = self.filters.to_sql(style=style)
        returning = self.get_returning()
        return (
            f"DELETE FROM\n  {self.table_name}\n{where}\n{returning}",
            args.for_sql(style),
        )


FieldDataType = NewType(
    "FieldDataType", Union[Dict, Collection[Tuple[Hashable, Any]], NamedTuple, Type]
)


def data_to_fields(data: FieldDataType, exclude: Any = Nothing) -> FieldList:
    """Convert a dataclass, NamedTuple, dict, or array of tuples to a FieldList.

    Parameters
    --------
    data
        Any data-source which you wish to conver to a list of fields.
    exclude
        Any value or type which you wish to exclude
    """
    if data:
        dict_factory = DictFactory(exclude=exclude)
        if dataclasses.is_dataclass(data):
            data = dataclasses.asdict(data, dict_factory=dict_factory)
        elif isnamedtuple(data):
            data = dict_factory(data._asdict())
        elif isinstance(data, Mapping) or (
            isinstance(data, Collection)
            and all((isinstance(x, Tuple) and len(x) == 2) for x in data)
        ):
            data = dict_factory(data)
        if isinstance(data, dict):
            return FieldList([Field(x, y) for x, y in data.items()])

    raise TypeError(
        "Data must not be empty and be of type dataclass, namedtuple, mapping, "
        f"or collection of tuples whose len is 2. Provided {type(data)}: {data}"
    )
