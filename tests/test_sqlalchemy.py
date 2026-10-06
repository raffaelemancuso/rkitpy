import pytest

sa = pytest.importorskip("sqlalchemy")

from rkitpy.sqlalchemy import duckdb_id_field, view  # noqa: E402


def test_duckdb_id_field_is_primary_key_named_id():
    col = duckdb_id_field("mytable")
    assert col.name == "id"
    assert col.primary_key is True


def test_view_created_and_dropped_in_sqlite():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    base = sa.Table(
        "base",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("val", sa.Integer),
    )
    view("myview", metadata, sa.select(base.c.id, base.c.val).where(base.c.val > 1))

    metadata.create_all(engine)
    assert "myview" in sa.inspect(engine).get_view_names()

    metadata.drop_all(engine)
    assert "myview" not in sa.inspect(engine).get_view_names()


def test_view_returns_selectable_table():
    metadata = sa.MetaData()
    base = sa.Table(
        "base2",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
    )
    t = view("v2", metadata, sa.select(base.c.id))
    assert "id" in t.c
