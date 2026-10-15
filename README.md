# dbx-readonly-sql starter

Minimal Python package for running exactly one read-only SELECT-family statement through an existing Databricks SQL connector connection.

- `validate_read_only_sql(query)` parses with SQLGlot's Databricks dialect.
- `execute_read_only(connection, query, parameters=None)` returns the connector's original `list[Row]` without changing values, labels, ordering, or SQL text, and **does not catch or wrap execution errors**.
- `execute_read_only_arrow(...)` returns the connector's `pyarrow.Table`, preserving Arrow column metadata and types.
- `execute_or_error(...)` returns either the original row list or the original exception object **as a value**. Choose this only if your application expects exceptions as returned values.

## Team install (from GitHub)

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install "git+https://github.com/Udayon-Paul-Dhrubo/dbx_readonly_sql.git@v0.1.0"
```

Set these environment variables (see `.env.example`; never commit real values):

- `DATABRICKS_SERVER_HOSTNAME`: from the SQL Warehouse *Connection details* tab, e.g. `adb-123.4.azuredatabricks.net` (no `https://`)
- `DATABRICKS_HTTP_PATH`: e.g. `/sql/1.0/warehouses/<id>`
- `DATABRICKS_TOKEN`: your own personal access token, or a shared read-only service principal token

To upgrade, change the `@v0.1.0` tag to the newest release.

## Install (development)

```bash
python -m pip install -e .
# for Arrow support:
python -m pip install -e '.[arrow]'
# for tests:
python -m pip install -e '.[test]'
pytest
```

Requires Python 3.10+, SQL Warehouse connection details, and working authentication.

## Usage (PAT demo)

Set `DATABRICKS_SERVER_HOSTNAME` (hostname only, no `https://`), `DATABRICKS_HTTP_PATH`, and `DATABRICKS_TOKEN` as environment variables.

```python
import os
from databricks import sql
from dbx_readonly_sql import execute_read_only, execute_or_error

with sql.connect(
    server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
) as connection:
    # Raw result (a list of native Row objects):
    rows = execute_read_only(connection, "SELECT * FROM samples.nyctaxi.trips LIMIT 2")
    print(rows)

    # Optional: unchanged error *object* as return value, not as exception:
    output = execute_or_error(connection, "SELECT * FROM nonexistent_table")
    if isinstance(output, Exception):
        print(type(output), output)
```

You may use service principal OAuth M2M instead of a personal access token; authentication is managed outside the package.

## Semantics and limitations

- Only `SELECT`, `WITH ... SELECT`, `UNION`, `INTERSECT`, `EXCEPT` are allowed. Read-only `SHOW`, `DESCRIBE`, `EXPLAIN` are deliberately rejected to keep the policy simple and fail-closed.
- A single SQL statement is required. Multiple statements, DML, DDL, command/execute nodes, `SELECT INTO`, and locking selects are rejected.
- SQLGlot is a parser, not a semantic SQL validator or a security sandbox. Some valid Databricks SQL may be rejected by this conservative policy; some invalid SQL may pass and then fail at Databricks.
- The original SQL text is submitted unchanged to Databricks; there is no SQL rewriting, auto-`LIMIT`, truncation, SQL error string conversion, retry, or row/type coercion in this package.
- `fetchall()` loads all rows into memory. Very large results should be streamed with `fetchmany()` / `fetchmany_arrow()`, retaining every row rather than silently limiting output.
- Protect against side effects with **least-privilege Databricks permissions**, not client-side parsing alone. Use a dedicated principal with only required `USE CATALOG`, `USE SCHEMA`, `SELECT` and SQL Warehouse access; withhold `MODIFY`, `CREATE`, write privileges, and execution of untrusted UDFs.
- Python and Databricks connectors naturally represent returned values and errors as Python objects. They do not recreate a byte-for-byte Databricks UI/REST payload.
- Unit tests (`pytest`) run locally without a Databricks connection.
