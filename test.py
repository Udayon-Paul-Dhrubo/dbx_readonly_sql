import os
from databricks import sql
from dbx_readonly_sql import execute_or_error

with sql.connect(
    server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
) as connection:

    result = execute_or_error(
        connection,
        """
        SELECT *
        FROM prod.cdw.cats_dbo_data_containe
        LIMIT 10
        """
    )

    if isinstance(result, Exception):
        # Original exception object, unchanged
        print(result)
    else:
        # Original list of Databricks Row objects
        print(result)
