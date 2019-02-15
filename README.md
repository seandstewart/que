Que: SQL for Sneks 🐍
================
[![image](https://img.shields.io/pypi/v/que-py.svg)](https://pypi.org/project/que-py/)
[![image](https://img.shields.io/pypi/l/que-py.svg)](https://pypi.org/project/que-py/)
[![image](https://img.shields.io/pypi/pyversions/que-py.svg)](https://pypi.org/project/que-py/)
[![image](https://img.shields.io/github/languages/code-size/seandstewart/que.svg?style=flat)](https://github.com/seandstewart/que)
[![image](https://img.shields.io/travis/seandstewart/que.svg)](https://travis-ci.org/seandstewart/que)
[![codecov](https://codecov.io/gh/seandstewart/que/branch/master/graph/badge.svg)](https://codecov.io/gh/seandstewart/que)

Que allows you to get generate your SQL queries on the fly, without the overhead of a fully-fledged ORM.

Motivations
--------
Que was born out of a need for dynamically generated SQL for an ASGI web service. I found my self wishing
for the convenience of dynamic querying with an ORM such as SQLAlchemy, but the performance of a fully
asynchronous database client. Que attempts to fill this void. Choose the connection client you prefer and
let Que worry about the SQL.


What Is It?
---------
Que looks to solve a single purpose: generate SQL-compliant queries in pure-Python. Que has absolutely no
hard dependendencies and does not enforce the use of a specific database client or dialect.

Still want to use SQLAlchemy for your connection? Go for it. Want to use PyMySQL or psycopg2? Que won't
stop you. Want to use an asyncio framework such as aiopg? You have excellent taste! This library was 
written just for you.


Design
-----
The focus of Que is *simplicity*, just look at what it takes for a simple `SELECT`:

```python
>>> import que
>>> select = que.Select(table='foo')
>>> select
Select(table='foo', schema=None, filters=FilterList([]), fields=FieldList([]))
>>> sql, args = select.to_sql()
>>> print(sql)
SELECT
  *
FROM
  foo

```

Que works with the DBAPI client of your choice by parametrizing your sql and formatting your arguments
for you:

```python
>>> import que
>>> fields = [que.Field('bar')]
>>> filters = [que.Filter(que.Field('id', 1))]
>>> select = que.Select(table='foo', filters=filters, fields=fields)
>>> sql, args = select.to_sql()
>>> print(sql)
SELECT
  bar
FROM
  foo
WHERE
  id = :1

>>> args
[1]
>>> sql, args = select.to_sql(style=que.NameParamStyle.NAME)
>>> print(sql)
SELECT
  bar
FROM
  foo
WHERE
  id = :id

>>> args
{'id': 1}

```

Que works to normalize the API for your SQL operations, so that initializing an `INSERT` or `UPDATE` is 
functionally the same as initializing a `SELECT`:

```python
>>> import que
>>> import dataclasses
>>> import datetime
>>>
>>> @dataclasses.dataclass
... class Foo:
...     bar: str
...     id: int = None
...     created: datetime.datetime = None
... 
>>> new_foo = Foo('blah')
>>> fields = que.data_to_fields(new_foo, exclude=None)
>>> insert = que.Insert(table='foo', fields=fields)
>>> sql, args = insert.to_sql(que.NameParamStyle.NAME)
>>> print(sql)
INSERT INTO
  foo (:colbar)
VALUES
  (:valbar)

>>> args
{'colbar': 'bar', 'valbar': 'blah'}

```
 
QuickStart
--------
Que has no dependencies and is exceptionally light-weight (currently only ~30Kb!), comprising of only a few hundred lines of code. 
Installation is as simple as `pip3 install que-py`.

Then you're good to go! `import que` and rock on 🤘


Examples
-------
A simple client for generating your SQL and inserting new entries:
```python
import dataclasses
import sqlite3

import que

@dataclasses.dataclass
class Spam:
    flavor: str
    id: int = None
    created_on: int = None
    

class SpamClient:
    """A database client for tracking spam flavors."""

    def __init__(self):
        self.conn = sqlite3.connect('sqlite://spam.db')
    
    def insert_spam(self, spam: Spam):
        fields = que.data_to_fields(spam, exclude=None)
        insert = que.Insert('spam', fields=fields)
        sql, args = insert.to_sql()
        return self.conn.execute(sql, args)
    
    def get_spam(self, **kwargs):
        fields = que.data_to_fields(kwargs)
        filters = [que.Filter(x) for x in fields]
        select = que.Select('spam', filters=filters)
        return self.conn.execute(*select.to_sql())
    
    def update_spam(self, spam: Spam):
        fields = [que.Field('flavor', spam.flavor)]
        filters = [que.Filter(que.Field('id', spam.id))]
        update = que.Update('spam', filters=filters, fields=fields)
        return self.conn.execute(*update.to_sql())
    
    def delete_spam(self, spam: Spam):
        filters = [que.Filter(que.Field('id', spam.id))]
        delete = que.Delete('spam', filters=filters)
        return self.conn.execute(*delete.to_sql())
```

Documentation
----------
Full documentation coming soon!

Happy Querying 🐍


How to Contribute
-----------------
1.  Check for open issues or open a fresh issue to start a discussion
    around a feature idea or a bug. 
2.  Create a branch on Github for your issue or fork [the repository](https://github.com/seandstewart/que) 
    on GitHub to start making your changes to the **master** branch.
3.  Write a test which shows that the bug was fixed or that the feature
    works as expected.
4.  Send a pull request and bug the maintainer until it gets merged and
    published. :)

