#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from dataclasses import dataclass, replace
from typing import NamedTuple

import pytest

import que


@pytest.fixture
def default_select() -> que.Select:
    field = que.Field("foo", "bar")
    fylter = que.Expression(field)
    select = que.Select(
        table="foo",
        schema="bar",
        fields=que.Fields((field,)),
        filters=que.Expressions((fylter,)),
    )
    return select


@pytest.fixture
def default_insert() -> que.Insert:
    field = que.Field("foo", "bar")
    insert = que.Insert(table="foo", schema="bar", fields=que.Fields((field,)))
    return insert


@pytest.fixture
def default_update() -> que.Update:
    field = que.Field("foo", "bar")
    fylter = que.Expression(field)
    update = que.Update(
        table="foo",
        schema="bar",
        fields=que.Fields((field,)),
        filters=que.Expressions((fylter,)),
    )
    return update


@pytest.fixture
def default_fields() -> que.Fields:
    return que.Fields([que.Field("foo", "bar")])


@pytest.fixture
def default_delete() -> que.Delete:
    field = que.Field("foo", "bar")
    fylter = que.Expression(field)
    delete = que.Delete(table="foo", schema="bar", filters=que.Expressions((fylter,)))
    return delete


def test_field_invalid():
    with pytest.raises(que.SQLSyntaxError):
        que.Field()


@pytest.mark.parametrize(
    argnames="style,statement",
    argvalues=[
        (
            que.NumParamStyle.NUM,
            "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = :1",
        ),
        (
            que.NumParamStyle.DOL,
            "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = $1",
        ),
        (
            que.NameParamStyle.NAME,
            "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = :foo",
        ),
        (
            que.NameParamStyle.PYFM,
            "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = %(foo)s",
        ),
        (
            que.BasicParamStyle.FM,
            "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = %s",
        ),
        (
            que.BasicParamStyle.QM,
            "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = ?",
        ),
    ],
)
def test_select(style, statement, default_select):
    sql, args = default_select.to_sql(style)
    assert sql == statement
    assert que.Arguments(default_select.fields) == args


def test_get_returning(default_delete):
    delete = replace(default_delete, returns=que.Field("id"))
    sql, args = delete.to_sql()
    assert sql.endswith("RETURNING id")


def test_delete(default_delete):
    sql, args = default_delete.to_sql()
    assert sql == "DELETE FROM bar.foo\n\nWHERE\n  foo = :1\n"


@pytest.mark.parametrize(
    argnames="style,statement",
    argvalues=[
        (
            que.NumParamStyle.NUM,
            "UPDATE\n  bar.foo\nSET\n  foo = :1\n\nWHERE\n  foo = :2\n",
        ),
        (
            que.NumParamStyle.DOL,
            "UPDATE\n  bar.foo\nSET\n  foo = $1\n\nWHERE\n  foo = $2\n",
        ),
        (
            que.NameParamStyle.NAME,
            "UPDATE\n  bar.foo\nSET\n  foo = :colfoo\n\nWHERE\n  foo = :foo\n",
        ),
        (
            que.NameParamStyle.PYFM,
            "UPDATE\n  bar.foo\nSET\n  foo = %(colfoo)s\n\nWHERE\n  foo = %(foo)s\n",
        ),
        (
            que.BasicParamStyle.FM,
            "UPDATE\n  bar.foo\nSET\n  foo = %s\n\nWHERE\n  foo = %s\n",
        ),
        (
            que.BasicParamStyle.QM,
            "UPDATE\n  bar.foo\nSET\n  foo = ?\n\nWHERE\n  foo = ?\n",
        ),
    ],
)
def test_update(style, statement, default_update):
    sql, args = default_update.to_sql(style)
    assert sql == statement
    if style in que.NameParamStyle:
        expected = que.Arguments(
            que.Fields((replace(f, left=f"col{f.left}") for f in default_update.fields))
            + que.Fields(default_update.filters.fields_to_sql(style))
        )
    else:
        expected = que.Arguments(
            default_update.fields
            + que.Fields(default_update.filters.fields_to_sql(style))
        )
    assert args == expected


@pytest.mark.parametrize(
    argnames="style,statement",
    argvalues=[
        (que.NumParamStyle.NUM, "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (:1)\n"),
        (que.NumParamStyle.DOL, "INSERT INTO\n  bar.foo (foo)\nVALUES\n  ($1)\n",),
        (
            que.NameParamStyle.NAME,
            "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (:valfoo)\n",
        ),
        (
            que.NameParamStyle.PYFM,
            "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (%(valfoo)s)\n",
        ),
        (que.BasicParamStyle.FM, "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (%s)\n",),
        (que.BasicParamStyle.QM, "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (?)\n",),
    ],
)
def test_insert(style, statement, default_insert):
    sql, args = default_insert.to_sql(style)
    assert sql == statement
    expected = que.Arguments(
        que.Fields(replace(f, left=f"val{f.left}") for f in default_insert.fields)
    )
    assert args == expected


def test_insert_inject_columns_false(default_insert):
    sql, args = default_insert.to_sql(inject_columns=False)
    assert sql == "INSERT INTO\n  bar.foo (:1)\nVALUES\n  (:2)\n"
    assert len(args) == 2


class FooTup(NamedTuple):
    foo: str


@dataclass
class FooBar:
    foo: str


@pytest.mark.parametrize(
    argnames="data",
    argvalues=[{"foo": "bar"}, [("foo", "bar")], FooTup("bar"), FooBar("bar")],
)
def test_data_to_fields_dict(data, default_fields):
    assert que.data_to_fields(data) == default_fields


def test_data_to_fields_invalid():
    with pytest.raises(que.SQLValueError):
        que.data_to_fields(["foo"])
    with pytest.raises(que.SQLValueError):
        que.data_to_fields([("foo",)])
