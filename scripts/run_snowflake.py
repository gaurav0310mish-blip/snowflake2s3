import os
import snowflake.connector

conn = snowflake.connector.connect(
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    role=os.environ["SNOWFLAKE_ROLE"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"]
)

cur = conn.cursor()
try:
    cur.execute("USE DATABASE TESTCATALOG_SF;")
    cur.execute("USE SCHEMA MY_SCHEMA;")

    # Call your Iceberg PARQUET procedure
    cur.execute("CALL CREATE_ALL_ICEBERG_TABLES_PARQUET();")

    print("Successfully executed Iceberg PARQUET build.")
finally:
    cur.close()
    conn.close()
