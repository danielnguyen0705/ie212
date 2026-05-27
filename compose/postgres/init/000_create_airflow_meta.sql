SELECT 'CREATE DATABASE airflow_meta OWNER stock_user'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'airflow_meta'
)
\gexec
