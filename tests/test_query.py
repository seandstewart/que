#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from dataclasses import dataclass, replace
from typing import NamedTuple

import pytest

import que
import que.query


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


def test_select_default_style(default_select):
    sql, args = default_select.to_sql()
    assert sql == "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = :1"
    assert que.Arguments(default_select.fields).for_sql() == args


def test_select_dollar_style(default_select):
    sql, args = default_select.to_sql(que.NumParamStyle.DOL)
    assert sql == "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = $1"
    assert que.Arguments(default_select.fields).for_sql(que.NumParamStyle.DOL) == args


def test_select_name_style(default_select):
    sql, args = default_select.to_sql(que.NameParamStyle.NAME)
    assert sql == "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = :foo"
    assert que.Arguments(default_select.fields).for_sql(que.NameParamStyle.NAME) == args


def test_select_pyformat_style(default_select):
    sql, args = default_select.to_sql(que.NameParamStyle.PYFM)
    assert sql == "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = %(foo)s"
    assert que.Arguments(default_select.fields).for_sql(que.NameParamStyle.PYFM) == args


def test_select_format_style(default_select):
    sql, args = default_select.to_sql(que.BasicParamStyle.FM)
    assert sql == "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = %s"
    assert que.Arguments(default_select.fields).for_sql(que.BasicParamStyle.FM) == args


def test_select_qmark_style(default_select):
    sql, args = default_select.to_sql(que.BasicParamStyle.QM)
    assert sql == "SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = ?"
    assert que.Arguments(default_select.fields).for_sql(que.BasicParamStyle.QM) == args


def test_delete(default_delete):
    sql, args = default_delete.to_sql()
    assert sql == "DELETE FROM\n  bar.foo\n\nWHERE\n  foo = :1\n"


def test_delete_get_returning(default_delete):
    delete = replace(default_delete, returns=que.Field("id"))
    sql, args = delete.to_sql()
    assert sql.endswith("RETURNING id")


def test_update_default_style(default_update):
    sql, args = default_update.to_sql()
    assert sql == "UPDATE\n  bar.foo\nSET\n  foo = :1\n\nWHERE\n  foo = :2\n"
    assert len(args) == 2


def test_update_dollar_style(default_update):
    sql, args = default_update.to_sql(que.NumParamStyle.DOL)
    assert sql == "UPDATE\n  bar.foo\nSET\n  foo = $1\n\nWHERE\n  foo = $2\n"
    assert len(args) == 2


def test_update_name_style(default_update):
    sql, args = default_update.to_sql(que.NameParamStyle.NAME)
    assert sql == "UPDATE\n  bar.foo\nSET\n  foo = :colfoo\n\nWHERE\n  foo = :foo\n"
    assert set(args) == {"colfoo", "foo"}


def test_update_pyformat_style(default_update):
    sql, args = default_update.to_sql(que.NameParamStyle.PYFM)
    assert (
        sql == "UPDATE\n  bar.foo\nSET\n  foo = %(colfoo)s\n\nWHERE\n  foo = %(foo)s\n"
    )
    assert set(args) == {"colfoo", "foo"}


def test_update_format_style(default_update):
    sql, args = default_update.to_sql(que.BasicParamStyle.FM)
    assert sql == "UPDATE\n  bar.foo\nSET\n  foo = %s\n\nWHERE\n  foo = %s\n"
    assert len(args) == 2


def test_update_qmark_style(default_update):
    sql, args = default_update.to_sql(que.BasicParamStyle.QM)
    assert sql == "UPDATE\n  bar.foo\nSET\n  foo = ?\n\nWHERE\n  foo = ?\n"
    assert len(args) == 2


def test_update_get_returning(default_update):
    update = replace(default_update, returns=que.Field("id"))
    sql, args = update.to_sql()
    assert sql.endswith("RETURNING id")


def test_insert_default_style(default_insert):
    sql, args = default_insert.to_sql()
    assert sql == "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (:2)\n"


def test_insert_inject_columns_false(default_insert):
    sql, args = default_insert.to_sql(inject_columns=False)
    assert sql == "INSERT INTO\n  bar.foo (:1)\nVALUES\n  (:2)\n"
    assert len(args) == 2


def test_insert_dollar_style(default_insert):
    sql, args = default_insert.to_sql(que.NumParamStyle.DOL)
    assert sql == "INSERT INTO\n  bar.foo (foo)\nVALUES\n  ($2)\n"
    assert len(args) == 1


def test_insert_name_style(default_insert):
    sql, args = default_insert.to_sql(que.NameParamStyle.NAME)
    assert sql == "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (:valfoo)\n"
    assert args.keys() == {"valfoo"}


def test_insert_pyformat_style(default_insert):
    sql, args = default_insert.to_sql(que.NameParamStyle.PYFM)
    assert sql == "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (%(valfoo)s)\n"
    assert args.keys() == {"valfoo"}


def test_insert_format_style(default_insert):
    sql, args = default_insert.to_sql(que.BasicParamStyle.FM)
    assert sql == "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (%s)\n"
    assert len(args) == 1


def test_insert_qmark_style(default_insert):
    sql, args = default_insert.to_sql(que.BasicParamStyle.QM)
    assert sql == "INSERT INTO\n  bar.foo (foo)\nVALUES\n  (?)\n"
    assert len(args) == 1


def test_insert_get_returning(default_insert):
    insert = replace(default_insert, returns=que.Field("id"))
    sql, args = insert.to_sql()
    assert sql.endswith("RETURNING id")


def test_data_to_fields_dict(default_fields):
    assert que.data_to_fields({"foo": "bar"}) == default_fields


def test_data_to_fields_list(default_fields):
    assert que.data_to_fields([("foo", "bar")]) == default_fields


def test_data_to_fields_named_tuple(default_fields):
    class FooBar(NamedTuple):
        foo: str

    assert que.data_to_fields(FooBar("bar")) == default_fields


def test_data_to_fields_dataclass(default_fields):
    @dataclass
    class FooBar:
        foo: str

    assert que.data_to_fields(FooBar("bar")) == default_fields


def test_data_to_fields_invalid():
    with pytest.raises(que.query.SQLValueError):
        que.data_to_fields(["foo"])
    with pytest.raises(que.query.SQLValueError):
        que.data_to_fields([("foo",)])
