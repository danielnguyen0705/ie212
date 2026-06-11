from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("outputs/performance")

PRODUCER_CONTAINER = "ie212-stock-producer"
SPARK_MASTER_CONTAINER = "ie212-spark-master"
ML_RUNNER_CONTAINER = "ie212-ml-infer"

SPARK_MASTER_URL = "spark://spark-master:7077"
KAFKA_BOOTSTRAP = "kafka:9092"
KAFKA_TOPIC = "stock-price"
SPARK_KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2"
POSTGRES_JDBC_PACKAGE = "org.postgresql:postgresql:42.7.10"

MINIO_ENDPOINT = "http://minio:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "change_me_minio"
MINIO_BUCKET = "processed"
MINIO_PREFIX = "kafka_ticks_parquet"

PG_HOST = "postgres"
PG_PORT = "5432"
PG_DB = "stock_project"
PG_USER = "stock_user"
PG_PASSWORD = "change_me_postgres"

MODEL_CHECKPOINT = "/workspace/models/tsn_attn_expanding_best_full.pt"
INFERENCE_RAW_DIR = "/workspace/data/raw"
INFERENCE_BUNDLE_PATH = "/workspace/data/inference/kafka_latest_window.npz"
INFERENCE_OUTPUT_JSON = "/workspace/outputs/inference/latest_prediction.json"
MODEL_NAME = "tsn_attn_expanding_best_full"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def docker_exec(container: str, cmd: list[str], timeout: int = 300) -> tuple[int, str, float]:
    full_cmd = ["docker", "exec", container, *cmd]
    start = time.perf_counter()
    proc = subprocess.run(full_cmd, capture_output=True, timeout=timeout, check=False)
    elapsed = time.perf_counter() - start
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    output = (stdout + "\n" + stderr).strip()
    return proc.returncode, output, elapsed


def count_pg_rows(table: str) -> int:
    import psycopg2
    conn = psycopg2.connect(host="localhost", port=15432, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            return cur.fetchone()[0]
    except Exception:
        return -1
    finally:
        conn.close()


def get_latest_prediction_count() -> int:
    import psycopg2
    conn = psycopg2.connect(host="localhost", port=15432, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM stock.inference_predictions "
                "WHERE prediction_run_id = ("
                "  SELECT prediction_run_id FROM stock.inference_predictions "
                "  GROUP BY prediction_run_id ORDER BY MAX(created_at) DESC LIMIT 1"
                ");"
            )
            return cur.fetchone()[0]
    except Exception:
        return -1
    finally:
        conn.close()


def kafka_log_end_offset() -> int:
    cmd = [
        "docker", "exec", "ie212-kafka",
        "/opt/kafka/bin/kafka-run-class.sh", "kafka.tools.GetOffsetShell",
        "--bootstrap-server", "localhost:9092",
        "--topic", KAFKA_TOPIC,
        "--time", "-1",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=30, check=False)
    total = 0
    for line in proc.stdout.strip().splitlines():
        parts = line.strip().split(":")
        if len(parts) == 3:
            total += int(parts[2])
    return total


def run_pipeline_once(run_id: str) -> dict[str, Any]:
    timestamps: dict[str, str] = {}
    step_metrics: list[dict[str, Any]] = []
    pipeline_start = time.perf_counter()
    timestamps["pipeline_start"] = utc_now()
    success = True
    error_msg = ""

    offset_before = kafka_log_end_offset()

    steps = [
        {
            "name": "publish_to_kafka",
            "component": "kafka_producer",
            "container": PRODUCER_CONTAINER,
            "cmd": [
                "python", "scripts/publish_stock_ticks.py",
                "--bootstrap-servers", KAFKA_BOOTSTRAP,
                "--topic", KAFKA_TOPIC,
                "--source", "csv",
                "--max-iterations", "1",
                "--interval-seconds", "0",
            ],
            "timeout": 120,
        },
        {
            "name": "spark_batch_to_postgres",
            "component": "spark",
            "container": SPARK_MASTER_CONTAINER,
            "cmd": [
                "/opt/spark/bin/spark-submit",
                "--master", SPARK_MASTER_URL,
                "--packages", f"{SPARK_KAFKA_PACKAGE},{POSTGRES_JDBC_PACKAGE}",
                "/opt/spark/jobs/write_kafka_batch_to_postgres.py",
            ],
            "timeout": 300,
        },
        {
            "name": "spark_batch_to_parquet",
            "component": "spark",
            "container": SPARK_MASTER_CONTAINER,
            "cmd": [
                "/opt/spark/bin/spark-submit",
                "--master", SPARK_MASTER_URL,
                "--packages", SPARK_KAFKA_PACKAGE,
                "/opt/spark/jobs/write_kafka_batch_to_parquet.py",
            ],
            "timeout": 300,
        },
        {
            "name": "sync_parquet_to_minio",
            "component": "minio",
            "container": ML_RUNNER_CONTAINER,
            "cmd": [
                "python", "-m", "scripts.sync_parquet_to_minio",
                "--local-dir", "/workspace/services/spark/out/kafka_ticks_parquet",
                "--minio-endpoint", MINIO_ENDPOINT,
                "--access-key", MINIO_ACCESS_KEY,
                "--secret-key", MINIO_SECRET_KEY,
                "--bucket", MINIO_BUCKET,
                "--prefix", MINIO_PREFIX,
            ],
            "timeout": 120,
        },
        {
            "name": "build_kafka_inference_bundle",
            "component": "ml_inference",
            "container": ML_RUNNER_CONTAINER,
            "cmd": [
                "python", "-m", "scripts.build_kafka_inference_bundle",
                "--data-dir", INFERENCE_RAW_DIR,
                "--output", INFERENCE_BUNDLE_PATH,
                "--minio-endpoint", MINIO_ENDPOINT,
                "--minio-access-key", MINIO_ACCESS_KEY,
                "--minio-secret-key", MINIO_SECRET_KEY,
                "--minio-bucket", MINIO_BUCKET,
                "--minio-prefix", MINIO_PREFIX,
            ],
            "timeout": 180,
        },
        {
            "name": "run_checkpoint_inference",
            "component": "ml_inference",
            "container": ML_RUNNER_CONTAINER,
            "cmd": [
                "python", "-m", "scripts.run_checkpoint_inference",
                "--checkpoint", MODEL_CHECKPOINT,
                "--input-npz", INFERENCE_BUNDLE_PATH,
                "--output-json", INFERENCE_OUTPUT_JSON,
                "--device", "cpu",
            ],
            "timeout": 120,
        },
        {
            "name": "save_inference_to_postgres",
            "component": "postgresql",
            "container": ML_RUNNER_CONTAINER,
            "cmd": [
                "python", "-m", "scripts.save_inference_to_postgres",
                "--input-json", INFERENCE_OUTPUT_JSON,
                "--model-name", f"{MODEL_NAME}-kafka-benchmark",
                "--prediction-run-id", run_id,
                "--pg-host", PG_HOST,
                "--pg-port", PG_PORT,
                "--pg-db", PG_DB,
                "--pg-user", PG_USER,
                "--pg-password", PG_PASSWORD,
            ],
            "timeout": 60,
        },
    ]

    for step in steps:
        timestamps[f"{step['name']}_start"] = utc_now()
        rc, output, elapsed = docker_exec(step["container"], step["cmd"], step["timeout"])
        timestamps[f"{step['name']}_end"] = utc_now()
        step_result = {
            "step": step["name"],
            "component": step["component"],
            "duration_s": round(elapsed, 4),
            "return_code": rc,
            "success": rc == 0,
        }
        step_metrics.append(step_result)
        if rc != 0:
            success = False
            error_msg = f"Step {step['name']} failed (rc={rc}): {output[:500]}"
            break

    pipeline_end = time.perf_counter()
    timestamps["pipeline_end"] = utc_now()
    total_duration = pipeline_end - pipeline_start

    offset_after = kafka_log_end_offset()
    messages_produced = offset_after - offset_before

    kafka_batch_rows = count_pg_rows("stock.kafka_ticks_batch") if success else -1
    prediction_rows = get_latest_prediction_count() if success else -1

    input_records = messages_produced if messages_produced > 0 else kafka_batch_rows
    completeness = round(prediction_rows / 10.0 * 100, 2) if prediction_rows > 0 else 0.0

    kafka_throughput = round(messages_produced / step_metrics[0]["duration_s"], 2) if success and step_metrics[0]["duration_s"] > 0 else 0

    spark_duration = sum(s["duration_s"] for s in step_metrics if s["component"] == "spark")
    spark_throughput = round(kafka_batch_rows / spark_duration, 2) if success and spark_duration > 0 and kafka_batch_rows > 0 else 0

    return {
        "run_id": run_id,
        "success": success,
        "error": error_msg if not success else None,
        "total_duration_s": round(total_duration, 4),
        "messages_produced": messages_produced,
        "kafka_batch_rows": kafka_batch_rows,
        "prediction_rows": prediction_rows,
        "data_completeness_pct": completeness,
        "kafka_producer_throughput_msg_per_s": kafka_throughput,
        "spark_processing_throughput_rec_per_s": spark_throughput,
        "step_metrics": step_metrics,
        "timestamps": timestamps,
    }


def evaluate_pipeline(runs: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(runs)
    successes = sum(1 for r in runs if r["success"])
    failures = total - successes
    success_rate = round(successes / total * 100, 2) if total > 0 else 0

    durations = [r["total_duration_s"] for r in runs if r["success"]]
    avg_duration = round(sum(durations) / len(durations), 4) if durations else 0

    completeness_values = [r["data_completeness_pct"] for r in runs if r["success"]]
    avg_completeness = round(sum(completeness_values) / len(completeness_values), 2) if completeness_values else 0

    def rate_status(val: float, good_thr: float, bad_thr: float, higher_better: bool = True) -> str:
        if higher_better:
            if val >= good_thr:
                return "good"
            if val >= bad_thr:
                return "acceptable"
            return "bad"
        else:
            if val <= good_thr:
                return "good"
            if val <= bad_thr:
                return "acceptable"
            return "bad"

    return {
        "total_runs": total,
        "successes": successes,
        "failures": failures,
        "success_rate_pct": success_rate,
        "success_rate_status": rate_status(success_rate, 90, 70),
        "avg_end_to_end_duration_s": avg_duration,
        "e2e_latency_status": rate_status(avg_duration, 120, 300, higher_better=False),
        "avg_data_completeness_pct": avg_completeness,
        "completeness_status": rate_status(avg_completeness, 99, 90),
        "failed_runs": [{"run_id": r["run_id"], "error": r.get("error")} for r in runs if not r["success"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark IE212 end-to-end pipeline.")
    parser.add_argument("--runs", type=int, default=3, help="Number of pipeline runs")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    all_runs: list[dict[str, Any]] = []
    for i in range(1, args.runs + 1):
        run_id = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}"
        print(f"\n{'='*60}")
        print(f"Pipeline run {i}/{args.runs}  (run_id={run_id})")
        print(f"{'='*60}")
        result = run_pipeline_once(run_id)
        all_runs.append(result)
        status = "OK" if result["success"] else "FAIL"
        print(f"  {status}  duration={result['total_duration_s']:.2f}s  completeness={result['data_completeness_pct']:.1f}%")

    evaluation = evaluate_pipeline(all_runs)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    detail_path = out_dir / "pipeline_benchmark_detail.json"
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump({"runs": all_runs, "evaluation": evaluation}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Pipeline Benchmark Summary")
    print(f"{'='*60}")
    print(f"  Runs: {evaluation['total_runs']} (success={evaluation['successes']}, fail={evaluation['failures']})")
    print(f"  Success rate: {evaluation['success_rate_pct']}% [{evaluation['success_rate_status']}]")
    print(f"  Avg E2E latency: {evaluation['avg_end_to_end_duration_s']}s [{evaluation['e2e_latency_status']}]")
    print(f"  Avg completeness: {evaluation['avg_data_completeness_pct']}% [{evaluation['completeness_status']}]")
    print(f"  Detail: {detail_path}")


if __name__ == "__main__":
    main()
