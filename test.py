import os

from dbx_readonly_sql import run_query

# Set these three environment variables before running (see .env.example).
result = run_query(
    """
    SELECT *
    FROM prod.cdw.cats_dbo_data_container
    LIMIT 10
    """,
    server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

if isinstance(result, Exception):
    print(result)  # the original exception object, unchanged
else:
    print(result)  # the original list of Databricks Row objects
