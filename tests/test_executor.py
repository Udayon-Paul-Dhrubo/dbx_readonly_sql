"""Package tests (run after installing with `pip install -e '.[test]'`)."""

from unittest.mock import MagicMock

import pytest
from sqlglot.errors import ParseError

from dbx_readonly_sql import (
    ReadOnlyQueryError,
    execute_or_error,
    execute_read_only,
    validate_read_only_sql,
)


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT 1",
        "SELECT 1;",
        "SELECT '; DELETE FROM t' AS value",
        "SELECT 1 -- DROP TABLE t",
        "WITH cte AS (SELECT 1 AS x) SELECT x FROM cte",
        "SELECT 1 UNION ALL SELECT 2",
    ],
)
def test_read_queries_pass(statement):
    validate_read_only_sql(statement)


@pytest.mark.parametrize(
    "statement",
    [
        "",
        "CREATE TABLE t AS SELECT 1",
        "INSERT INTO t SELECT 1",
        "UPDATE t SET id = 1",
        "DELETE FROM t",
        "MERGE INTO t USING s ON t.id = s.id WHEN MATCHED THEN DELETE",
        "DROP TABLE t",
        "TRUNCATE TABLE t",
        "CALL do_something()",
        "SELECT 1; DROP TABLE t",
        "SELECT 1; SELECT 2",
        "SHOW TABLES",  # Deliberately outside the minimal SELECT-only policy.
    ],
)
def test_unsafe_or_non_select_queries_rejected(statement):
    with pytest.raises((ReadOnlyQueryError, ParseError)):
        validate_read_only_sql(statement)


def _connection_with(cursor):
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    return connection


def test_sql_and_rows_are_passed_through():
    raw_rows = [object(), object()]
    cursor = MagicMock()
    cursor.fetchall.return_value = raw_rows
    connection = _connection_with(cursor)
    statement = "SELECT 1 AS number"

    output = execute_read_only(connection, statement)

    assert output is raw_rows
    cursor.execute.assert_called_once_with(statement)


def test_parameters_preserved():
    cursor = MagicMock()
    connection = _connection_with(cursor)
    params = {"min_id": 10}
    execute_read_only(connection, "SELECT :min_id", params)
    cursor.execute.assert_called_once_with("SELECT :min_id", parameters=params)


def test_native_databricks_exception_instance_passed_through():
    native_error = RuntimeError("[TABLE_OR_VIEW_NOT_FOUND] SQLSTATE: 42P01")
    cursor = MagicMock()
    cursor.execute.side_effect = native_error
    connection = _connection_with(cursor)

    with pytest.raises(RuntimeError) as result:
        execute_read_only(connection, "SELECT * FROM missing_table")

    assert result.value is native_error
    assert execute_or_error(connection, "SELECT * FROM missing_table") is native_error


def test_unsafe_queries_are_never_executed():
    cursor = MagicMock()
    connection = _connection_with(cursor)

    with pytest.raises(ReadOnlyQueryError):
        execute_read_only(connection, "DELETE FROM t")

    connection.cursor.assert_not_called()
