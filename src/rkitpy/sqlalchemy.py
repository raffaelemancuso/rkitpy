# rkitpy Miscellaneous functions
# Copyright (C) 2026 Raffaele Mancuso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sqlalchemy as sa
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement


def duckdb_id_field(table_name: str):
    """
    Create an auto-incrementing ID column for DuckDB.

    :param table_name: Name of the table (used to create the sequence name).
    :type table_name: str
    :return: A SQLAlchemy Column with auto-incrementing integer ID.
    :rtype: sqlalchemy.Column
    """
    sequence = sa.Sequence(f"{table_name}_id_seq")
    col = sa.Column(
        "id",
        sa.Integer,
        sequence,
        server_default=sequence.next_value(),
        primary_key=True,
    )
    return col


# VIEW
# See: https://github.com/sqlalchemy/sqlalchemy/wiki/Views


class CreateView(DDLElement):
    """DDL element for creating a database view."""

    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    """DDL element for dropping a database view."""

    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def _create_view(element, compiler, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        compiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


@compiler.compiles(DropView)
def _drop_view(element, compiler, **kw):
    return "DROP VIEW %s" % (element.name)


def view_exists(ddl, target, connection, **kw):
    """
    Check if a view exists in the database.

    :param ddl: The DDL element.
    :param target: The target schema item.
    :param connection: Database connection.
    :param kw: Additional keyword arguments.
    :return: True if the view exists, False otherwise.
    :rtype: bool
    """
    return ddl.name in sa.inspect(connection).get_view_names()


def view_doesnt_exist(ddl, target, connection, **kw):
    """
    Check if a view does not exist in the database.

    :param ddl: The DDL element.
    :param target: The target schema item.
    :param connection: Database connection.
    :param kw: Additional keyword arguments.
    :return: True if the view does not exist, False otherwise.
    :rtype: bool
    """
    return not view_exists(ddl, target, connection, **kw)


def view(name, metadata, selectable):
    """
    Create a SQLAlchemy view with automatic create/drop DDL events.

    :param name: Name of the view to create.
    :param metadata: SQLAlchemy Metadata object.
    :param selectable: A SELECT statement or query to use as the view definition.
    :return: A SQLAlchemy table object representing the view.
    :rtype: sqlalchemy.sql.expression.TableClause
    """

    t = sa.table(
        name,
        *(
            sa.Column(c.name, c.type, primary_key=c.primary_key)
            for c in selectable.selected_columns
        ),
    )
    t.primary_key.update(c for c in t.c if c.primary_key)

    sa.event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=view_doesnt_exist),
    )
    sa.event.listen(
        metadata,
        "before_drop",
        DropView(name).execute_if(callable_=view_exists),
    )
    return t
