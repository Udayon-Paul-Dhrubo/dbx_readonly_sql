"""Read-only Databricks SQL validation and connector pass-through.

The AST check is intentionally conservative. It is NOT a substitute for
least-privilege authorization in Databricks / Unity Catalog.
"""

from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ErrorLevel


class ReadOnlyQueryError(ValueError):
    """The provided statement is outside the allowed read-only SQL subset."""


def validate_read_only_sql(sql_text: str) -> None:
    """Allow one SELECT-family statement; reject potentially mutating constructs.

    SQLGlot ParseError is intentionally not caught or converted. SQLGlot is a
    parser, not a full SQL semantic validator; Databricks may reject SQL
    accepted here, and valid new syntax may be conservatively rejected.
    """
    if not isinstance(sql_text, str) or not sql_text.strip():
        raise ReadOnlyQueryError("SQL must be a non-empty string")

    # Use Databricks grammar, and never silently ignore parsing failures.
    parsed = sqlglot.parse(sql_text, read="databricks", error_level=ErrorLevel.RAISE)
    statements = [stmt for stmt in parsed if stmt is not None]

    if len(statements) != 1:
        raise ReadOnlyQueryError("Exactly one SQL statement is allowed")

    statement = statements[0]
    if not isinstance(statement, (exp.Select, exp.SetOperation)):
        raise ReadOnlyQueryError(
            "Only SELECT, WITH ... SELECT, UNION, INTERSECT, and EXCEPT queries are allowed"
        )

    for node in statement.walk():
        # Reject writes or arbitrary commands anywhere, including inside CTEs.
        if isinstance(node, (exp.DDL, exp.DML, exp.Command, exp.Execute)):
            raise ReadOnlyQueryError("Write/command statements are not allowed")

        # Some dialects parse SELECT INTO or locking reads as a SELECT root.
        if isinstance(node, exp.Select) and any(
            node.args.get(key) is not None for key in ("into", "locks", "for_")
        ):
            raise ReadOnlyQueryError("SELECT INTO or locking SELECT is not allowed")


def _execute(connection: Any, sql_text: str, parameters: Any, fetch_method: str) -> Any:
    validate_read_only_sql(sql_text)

    with connection.cursor() as cursor:
        # Pass the original SQL literally, not SQLGlot's formatted SQL.
        if parameters is None:
            cursor.execute(sql_text)
        else:
            cursor.execute(sql_text, parameters=parameters)

        # Return the connector's original result object (no JSON or reshaping).
        return getattr(cursor, fetch_method)()


def execute_read_only(connection: Any, sql_text: str, parameters: Any = None) -> Any:
    """Return raw connector ``list[Row]``. Native exceptions propagate unchanged."""
    return _execute(connection, sql_text, parameters, "fetchall")


def execute_read_only_arrow(connection: Any, sql_text: str, parameters: Any = None) -> Any:
    """Return raw ``pyarrow.Table`` with column metadata; requires PyArrow."""
    return _execute(connection, sql_text, parameters, "fetchall_arrow")


def execute_or_error(connection: Any, sql_text: str, parameters: Any = None) -> Any:
    """Return native rows or the *same exception instance*, without serialization.

    This is convenient for callers requiring returned errors rather than raised
    exceptions. The return type is a union of list[Row] and Exception.
    """
    try:
        return execute_read_only(connection, sql_text, parameters)
    except Exception as exc:
        return exc
