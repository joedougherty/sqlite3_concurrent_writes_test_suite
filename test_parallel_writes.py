import pytest


from database import create_table, row_count, insert_row
from utils import (
    insert_rows_in_parallel,
    insert_rows_in_parallel_cf,
    generate_example_rows,
)


def test_adding_5_rows_in_parallel_to_new_db():
    # Create a new `messages` sqlite3 table,
    # dropping it if one already exists.
    create_table()

    assert row_count() == 0

    # Run 5 parallel instances of `insert_rows`
    # by way of `insert_rows_in_parallel`
    insert_rows_in_parallel(generate_example_rows(5))

    assert row_count() == 5


def test_adding_50_rows_in_parallel_to_new_db():
    create_table()

    assert row_count() == 0

    insert_rows_in_parallel(generate_example_rows(50))

    assert row_count() == 50


def test_adding_250_rows_in_parallel_to_new_db():
    create_table()

    assert row_count() == 0

    insert_rows_in_parallel(generate_example_rows(250))

    assert row_count() == 250


def test_adding_250_rows_in_parallel_to_new_db_cf():
    create_table()

    assert row_count() == 0

    insert_rows_in_parallel_cf(generate_example_rows(250))

    assert row_count() == 250


def test_adding_50_rows_to_populated_db():
    # Row count from previous test should remain unchanged
    assert row_count() == 250

    insert_rows_in_parallel(generate_example_rows(50))

    assert row_count() == 300


def test_adding_10000_rows_sequentially_then_100_rows_in_parallel():
    create_table()

    assert row_count() == 0

    for example_row in generate_example_rows(10000):
        insert_row(example_row)

    assert row_count() == 10000

    insert_rows_in_parallel(generate_example_rows(100))

    assert row_count() == 10100


def test_adding_250_rows_in_parallel_to_new_db_wal_mode_enabled():
    # After creating the database, enable WAL mode.
    # https://www.sqlite.org/pragma.html#pragma_journal_mode
    create_table(enable_wal_mode=True)

    assert row_count() == 0

    insert_rows_in_parallel(generate_example_rows(250))

    assert row_count() == 250


def test_adding_500_rows_in_parallel_to_new_db_wal_mode_enabled():
    # After creating the database, enable WAL mode.
    # https://www.sqlite.org/pragma.html#pragma_journal_mode
    create_table(enable_wal_mode=True)

    assert row_count() == 0

    insert_rows_in_parallel(generate_example_rows(500))

    assert row_count() == 500
