from datetime import datetime
from airflow.sdk import dag, task


@dag(
    dag_id="ie212_smoke_test",
    schedule=None,
    start_date=datetime(2026, 4, 15),
    catchup=False,
    tags=["ie212", "smoke-test"],
)
def ie212_smoke_test():
    @task
    def hello():
        print("IE212 Airflow smoke test is running.")
        return "ok"

    @task
    def summary(status: str):
        print(f"Pipeline status: {status}")

    summary(hello())


ie212_smoke_test()