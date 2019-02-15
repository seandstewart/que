#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from dataclasses import dataclass
from typing import NamedTuple

import pytest

import que
import que.query


@pytest.fixture
def default_select() -> que.Select:
    field = que.Field('foo', 'bar')
    fylter = que.Filter(field)
    select = que.Select(table='foo', schema='bar', fields=[field], filters=[fylter])
    return select


@pytest.fixture
def default_insert() -> que.Insert:
    field = que.Field('foo', 'bar')
    insert = que.Insert(table='foo', schema='bar', fields=[field])
    return insert


@pytest.fixture
def default_update() -> que.Update:
    field = que.Field('foo', 'bar')
    fylter = que.Filter(field)
    update = que.Update(table='foo', schema='bar', fields=[field], filters=[fylter])
    return update


@pytest.fixture
def default_field_list() -> que.FieldList:
    return que.FieldList([que.Field('foo', 'bar')])


@pytest.fixture
def default_delete() -> que.Delete:
    field = que.Field('foo', 'bar')
    fylter = que.Filter(field)
    delete = que.Delete(table='foo', schema='bar', filters=[fylter])
    return delete


def test_field_invalid():
    with pytest.raises(TypeError):
        que.Field()


def test_filter_invalid():
    with pytest.raises(TypeError):
        que.Filter(que.Field('foo'))


def test_base_write_invalid(default_field_list):
    default_field_list[0].name = None
    with pytest.raises(TypeError):
        que.query._BaseWriteStatement('foo', 'bar', fields=default_field_list)


def test_select_default_style(default_select):
    sql, args = default_select.to_sql()
    assert sql == 'SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = :1'
    assert que.ArgList(default_select.fields).for_sql() == args


def test_select_dollar_style(default_select):
    sql, args = default_select.to_sql(que.NumParamStyle.DOL)
    assert sql == 'SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = $1'
    assert que.ArgList(default_select.fields).for_sql(que.NumParamStyle.DOL) == args


def test_select_name_style(default_select):
    sql, args = default_select.to_sql(que.NameParamStyle.NAME)
    assert sql == 'SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = :foo'
    assert que.ArgList(default_select.fields).for_sql(que.NameParamStyle.NAME) == args


def test_select_pyformat_style(default_select):
    sql, args = default_select.to_sql(que.NameParamStyle.PYFM)
    assert sql == 'SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = %(foo)s'
    assert que.ArgList(default_select.fields).for_sql(que.NameParamStyle.PYFM) == args


def test_select_format_style(default_select):
    sql, args = default_select.to_sql(que.BasicParamStyle.FM)
    assert sql == 'SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = %s'
    assert que.ArgList(default_select.fields).for_sql(que.BasicParamStyle.FM) == args


def test_select_qmark_style(default_select):
    sql, args = default_select.to_sql(que.BasicParamStyle.QM)
    assert sql == 'SELECT\n  foo AS bar\nFROM\n  bar.foo\nWHERE\n  foo = ?'
    assert que.ArgList(default_select.fields).for_sql(que.BasicParamStyle.QM) == args


def test_delete(default_delete):
    sql, args = default_delete.to_sql()
    assert sql == 'DELETE FROM\n  bar.foo\nWHERE\n  foo = :1\n'


def test_delete_get_returning(default_delete):
    default_delete.returns = que.Field('id')
    sql, args = default_delete.to_sql()
    assert sql.endswith('RETURNING id')


def test_update_default_style(default_update):
    sql, args = default_update.to_sql()
    assert sql == 'UPDATE\n  bar.foo\nSET\n  foo = :1\nWHERE\n  foo = :2\n'


def test_update_dollar_style(default_update):
    sql, args = default_update.to_sql(que.NumParamStyle.DOL)
    assert sql == 'UPDATE\n  bar.foo\nSET\n  foo = $1\nWHERE\n  foo = $2\n'


def test_update_name_style(default_update):
    sql, args = default_update.to_sql(que.NameParamStyle.NAME)
    assert sql == 'UPDATE\n  bar.foo\nSET\n  foo = :colfoo\nWHERE\n  foo = :foo\n'


def test_update_pyformat_style(default_update):
    sql, args = default_update.to_sql(que.NameParamStyle.PYFM)
    assert sql == 'UPDATE\n  bar.foo\nSET\n  foo = %(colfoo)s\nWHERE\n  foo = %(foo)s\n'


def test_update_format_style(default_update):
    sql, args = default_update.to_sql(que.BasicParamStyle.FM)
    assert sql == 'UPDATE\n  bar.foo\nSET\n  foo = %s\nWHERE\n  foo = %s\n'


def test_update_qmark_style(default_update):
    sql, args = default_update.to_sql(que.BasicParamStyle.QM)
    assert sql == 'UPDATE\n  bar.foo\nSET\n  foo = ?\nWHERE\n  foo = ?\n'


def test_update_get_returning(default_update):
    default_update.returns = que.Field('id')
    sql, args = default_update.to_sql()
    assert sql.endswith('RETURNING id')


def test_insert_default_style(default_insert):
    sql, args = default_insert.to_sql()
    assert sql == 'INSERT INTO\n  bar.foo (:1)\nVALUES\n  (:2)\n'


def test_insert_dollar_style(default_insert):
    sql, args = default_insert.to_sql(que.NumParamStyle.DOL)
    assert sql == 'INSERT INTO\n  bar.foo ($1)\nVALUES\n  ($2)\n'


def test_insert_name_style(default_insert):
    sql, args = default_insert.to_sql(que.NameParamStyle.NAME)
    assert sql == 'INSERT INTO\n  bar.foo (:colfoo)\nVALUES\n  (:valfoo)\n'


def test_insert_pyformat_style(default_insert):
    sql, args = default_insert.to_sql(que.NameParamStyle.PYFM)
    assert sql == 'INSERT INTO\n  bar.foo (%(colfoo)s)\nVALUES\n  (%(valfoo)s)\n'


def test_insert_format_style(default_insert):
    sql, args = default_insert.to_sql(que.BasicParamStyle.FM)
    assert sql == 'INSERT INTO\n  bar.foo (%s)\nVALUES\n  (%s)\n'


def test_insert_qmark_style(default_insert):
    sql, args = default_insert.to_sql(que.BasicParamStyle.QM)
    assert sql == 'INSERT INTO\n  bar.foo (?)\nVALUES\n  (?)\n'


def test_insert_get_returning(default_insert):
    default_insert.returns = que.Field('id')
    sql, args = default_insert.to_sql()
    assert sql.endswith('RETURNING id')


def test_data_to_fields_dict(default_field_list):
    assert que.data_to_fields({'foo': 'bar'}) == default_field_list


def test_data_to_fields_list(default_field_list):
    assert que.data_to_fields([('foo', 'bar')]) == default_field_list


def test_data_to_fields_named_tuple(default_field_list):
    class FooBar(NamedTuple):
        foo: str
    assert que.data_to_fields(FooBar('bar')) == default_field_list


def test_data_to_fields_dataclass(default_field_list):
    @dataclass
    class FooBar:
        foo: str
    assert que.data_to_fields(FooBar('bar')) == default_field_list


def test_data_to_fields_empty():
    with pytest.raises(TypeError):
        que.data_to_fields([])


def test_data_to_fields_invalid():
    with pytest.raises(TypeError):
        que.data_to_fields(['foo'])
    with pytest.raises(TypeError):
        que.data_to_fields([('foo',)])


def test_write_invalid():
    with pytest.raises(TypeError):
        que.Insert('foo', fields=[que.Field(value='foo')])


def test_append_fieldlist_invalid():
    with pytest.raises(TypeError):
        que.FieldList().append('foo')


def test_append_filterlist():
    fylter = que.Filter(que.Field('foo', 'bar'))
    lyst = que.FilterList()
    lyst.append(fylter)
    assert fylter in lyst


def test_append_filterlist_invalid():
    with pytest.raises(TypeError):
        que.FilterList().append('foo')
