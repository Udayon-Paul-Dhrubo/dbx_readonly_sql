"""Read-only Databricks SQL pass-through functions."""

from .executor import (
    ReadOnlyQueryError,
    execute_or_error,
    execute_read_only,
    execute_read_only_arrow,
    validate_read_only_sql,
)

__all__ = [
    "ReadOnlyQueryError",
    "execute_or_error",
    "execute_read_only",
    "execute_read_only_arrow",
    "validate_read_only_sql",
]
