
from . import base

import datetime

import sqlite3


class sqlite(base.driver_base):
    """Driver for sqlite3 databases

    sqlite accepts only one parameter: path, which is the path of the database
    file. By default, path=':memory:', which creates a temporary database
    in memory.

    The following are equivalent:

    >>> mydb = DB() #sqlite is used as the default database

    >>> mydb = DB.connect('sqlite')

    >>> mydb = DB.connect('sqlite', ':memory:')
    """
    id_quote = '"'

    def __init__(self, path=':memory:', debug=False):
        self.path = path
        self.__db_api_init__(sqlite3, path, sqlite3.PARSE_DECLTYPES,
                             debug=debug)

    def normalize_column(self, column):
        r = base.driver_base.normalize_column(self, column)
        if r.primarykey:
            r.autoinc_sql = ''
        return r

    webdb_types = {
        int: 'INTEGER',
        float: 'REAL',
        bool: 'INT',
        str: 'TEXT',
        bytes: 'BLOB',
        datetime.datetime: 'TIMESTAMP',
    }

    driver_types = {
        'TEXT': str,
        'INTEGER': int,
        'REAL': float,
        'BLOB': bytes,
        'TIMESTAMP': datetime.datetime,
    }

    def handle_exception(self, e):
        if isinstance(e, sqlite3.OperationalError):
            msg = e.args[0]
            if ('has no column named' in msg or
                    msg.startswith('no such column: ')):
                raise KeyError(
                    "No such column in table: %s" % msg.rsplit(None, 1)[1])
            if msg == 'unable to open database file':
                raise base.make_IOError(
                    'ENOENT', 'No such file or directory: %r' % self.path)
            if msg.endswith(': syntax error'):
                text = msg.partition('"')[2].rpartition('"')[0]
                offset = self.lastsql.index(text)
                raise base.SQLSyntaxError(self.lastsql, offset, text)
        elif isinstance(e, sqlite3.IntegrityError):
            msg = e.args[0]
            if msg.startswith('UNIQUE constraint failed: '):
                raise ValueError(msg)

    def list_tables_sql(self):
        return """SELECT name FROM sqlite_master WHERE type='table'"""

    def list_columns(self, table):
        for _, name, v_type, notnull, default, _ in self.execute(
                """PRAGMA table_info(%s);""" % table):
            yield (str(name), self.unmap_type(v_type), bool(notnull), default)

    def create_table_if_nexists_sql(self, name, coldefs, primarykeys):
        return """CREATE TABLE IF NOT EXISTS %s(%s%s);""" % (
            name, ', '.join(coldefs), (
                (', PRIMARY KEY (%s)' % ', '.join(
                    '%s ASC' % p for p in primarykeys))
                if primarykeys else ''))

    def _drop_column(self, table, column):
        raise NotImplementedError
