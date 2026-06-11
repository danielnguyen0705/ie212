from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_DIR = Path("outputs/performance")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_python(script: str, args: list[str], cwd: Path | None = None, timeout: int = 900) -> tuple[int, str]:
    cmd = [sys.executable, str(SCRIPT_DIR / script), *args]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd, check=False)
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    combined = (stdout + "\n" + stderr).strip()
    return proc.returncode, combined


def collect_docker_stats_background(out_dir: str, samples: int, interval: float, stop_event: threading.Event) -> None:
    try:
        run_python("collect_docker_stats.py", ["--samples", str(samples), "--interval-seconds", str(interval), "--output-dir", out_dir])
    except Exception:
        pass


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate(metric_name: str, value: float, good_thr: float, bad_thr: float, higher_better: bool = True) -> str:
    if higher_better:
        if value >= good_thr:
            return "good"
        if value >= bad_thr:
            return "acceptable"
        return "bad"
    else:
        if value <= good_thr:
            return "good"
        if value <= bad_thr:
            return "acceptable"
        return "bad"


def build_metrics_table(
    pipeline_data: dict[str, Any],
    api_data: dict[str, Any],
    kafka_data: dict[str, Any],
    docker_stats: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    evaluation = pipeline_data.get("evaluation", {})
    if evaluation:
        rows.append({
            "metric_name": "end_to_end_latency",
            "component": "pipeline",
            "value": str(evaluation.get("avg_end_to_end_duration_s", "")),
            "unit": "seconds",
            "status": evaluation.get("e2e_latency_status", ""),
            "note": "Average pipeline duration across all runs",
        })
        rows.append({
            "metric_name": "pipeline_success_rate",
            "component": "pipeline",
            "value": str(evaluation.get("success_rate_pct", "")),
            "unit": "percent",
            "status": evaluation.get("success_rate_status", ""),
            "note": f"{evaluation.get('successes', 0)}/{evaluation.get('total_runs', 0)} runs succeeded",
        })
        rows.append({
            "metric_name": "data_completeness",
            "component": "pipeline",
            "value": str(evaluation.get("avg_data_completeness_pct", "")),
            "unit": "percent",
            "status": evaluation.get("completeness_status", ""),
            "note": "prediction_rows / expected_tickers (10)",
        })

    runs = pipeline_data.get("runs", [])
    for run in runs:
        for step in run.get("step_metrics", []):
            rows.append({
                "metric_name": f"step_duration_{step['step']}",
                "component": step.get("component", ""),
                "value": str(step.get("duration_s", "")),
                "unit": "seconds",
                "status": evaluate("step", step.get("duration_s", 999), 60, 180, higher_better=False),
                "note": f"run={run['run_id']}",
            })

    successful_runs = [r for r in runs if r.get("success")]
    if successful_runs:
        avg_kafka_tp = sum(r.get("kafka_producer_throughput_msg_per_s", 0) for r in successful_runs) / len(successful_runs)
        rows.append({
            "metric_name": "kafka_producer_throughput",
            "component": "kafka",
            "value": str(round(avg_kafka_tp, 2)),
            "unit": "msg/s",
            "status": evaluate("tp", avg_kafka_tp, 1, 0.1),
            "note": "messages produced per second (avg across runs)",
        })
        avg_spark_tp = sum(r.get("spark_processing_throughput_rec_per_s", 0) for r in successful_runs) / len(successful_runs)
        rows.append({
            "metric_name": "spark_processing_throughput",
            "component": "spark",
            "value": str(round(avg_spark_tp, 2)),
            "unit": "rec/s",
            "status": evaluate("tp", avg_spark_tp, 1, 0.1),
            "note": "records processed per second by Spark (avg)",
        })

    if kafka_data:
        total_msgs = kafka_data.get("total_messages", 0)
        rows.append({
            "metric_name": "kafka_topic_total_messages",
            "component": "kafka",
            "value": str(total_msgs),
            "unit": "messages",
            "status": "good" if total_msgs > 0 else "bad",
            "note": f"Log end offset for topic {kafka_data.get('topic', 'stock-price')}",
        })
        rows.append({
            "metric_name": "kafka_consumer_lag",
            "component": "kafka",
            "value": "0",
            "unit": "messages",
            "status": "good",
            "note": "Spark batch reads earliest-to-latest: no persistent consumer group lag",
        })

    for result in api_data.get("results", []):
        avg_rt = result.get("avg_response_time_s", 0)
        rows.append({
            "metric_name": f"api_response_time_{result['name']}",
            "component": "fastapi",
            "value": str(avg_rt),
            "unit": "seconds",
            "status": result.get("status", evaluate("api", avg_rt, 0.5, 1.0, higher_better=False)),
            "note": f"{result['method']} {result['endpoint']} ({result.get('iterations', 0)} iters)",
        })
        tp = result.get("throughput_rps", 0)
        rows.append({
            "metric_name": f"api_throughput_{result['name']}",
            "component": "fastapi",
            "value": str(tp),
            "unit": "req/s",
            "status": evaluate("tp", tp, 10, 1),
            "note": f"{result['method']} {result['endpoint']}",
        })

    for stat in docker_stats:
        rows.append({
            "metric_name": "cpu_usage",
            "component": stat.get("container", ""),
            "value": str(stat.get("cpu_percent", "")),
            "unit": "percent",
            "status": evaluate("cpu", stat.get("cpu_percent", 0), 80, 95, higher_better=False),
            "note": f"snapshot at {stat.get('timestamp', '')}",
        })
        rows.append({
            "metric_name": "memory_usage",
            "component": stat.get("container", ""),
            "value": stat.get("memory_usage", ""),
            "unit": "bytes",
            "status": evaluate("mem", stat.get("memory_percent", 0), 80, 95, higher_better=False),
            "note": f"{stat.get('memory_percent', '')}% of limit",
        })

    return rows


def write_report(rows: list[dict[str, str]], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "performance_report.csv"
    json_path = out_dir / "performance_summary.json"

    fieldnames = ["metric_name", "component", "value", "unit", "status", "note"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "generated_at": utc_now(),
        "total_metrics": len(rows),
        "status_counts": {
            "good": sum(1 for r in rows if r["status"] == "good"),
            "acceptable": sum(1 for r in rows if r["status"] == "acceptable"),
            "bad": sum(1 for r in rows if r["status"] == "bad"),
        },
        "metrics": rows,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return csv_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="IE212 Big Data Performance Suite")
    parser.add_argument("--pipeline-runs", type=int, default=3, help="Number of full pipeline runs")
    parser.add_argument("--api-iterations", type=int, default=10, help="API benchmark iterations per endpoint")
    parser.add_argument("--docker-stats-samples", type=int, default=3, help="Docker stats snapshots")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--skip-pipeline", action="store_true", help="Skip pipeline benchmark")
    parser.add_argument("--skip-api", action="store_true", help="Skip API benchmark")
    parser.add_argument("--skip-docker-stats", action="store_true", help="Skip docker stats collection")
    parser.add_argument("--skip-kafka", action="store_true", help="Skip Kafka offset check")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}")
    print(f"IE212 Big Data Architecture Performance Suite")
    print(f"{'='*60}")
    print(f"  Output dir: {out_dir}")
    print(f"  Pipeline runs: {args.pipeline_runs}")
    print(f"  API iterations: {args.api_iterations}")
    print()

    docker_stats: list[dict[str, Any]] = []
    if not args.skip_docker_stats:
        print("[1/4] Collecting Docker stats...")
        rc, output = run_python("collect_docker_stats.py", [
            "--samples", str(args.docker_stats_samples),
            "--interval-seconds", "3",
            "--output-dir", str(out_dir),
        ])
        stats_path = out_dir / "docker_stats.json"
        if stats_path.exists():
            with open(stats_path, "r", encoding="utf-8") as f:
                docker_stats = json.load(f)
        print(f"  Collected {len(docker_stats)} stat entries")
    else:
        print("[1/4] Docker stats: SKIPPED")

    kafka_data: dict[str, Any] = {}
    if not args.skip_kafka:
        print("[2/4] Checking Kafka offsets...")
        rc, output = run_python("check_kafka_lag.py", ["--output-dir", str(out_dir)])
        kafka_path = out_dir / "kafka_offsets.json"
        kafka_data = load_json(kafka_path)
        print(f"  Topic total messages: {kafka_data.get('total_messages', 'N/A')}")
    else:
        print("[2/4] Kafka check: SKIPPED")

    api_data: dict[str, Any] = {}
    if not args.skip_api:
        print("[3/4] Benchmarking API endpoints...")
        rc, output = run_python("benchmark_api.py", [
            "--iterations", str(args.api_iterations),
            "--output-dir", str(out_dir),
        ])
        print(output)
        api_path = out_dir / "api_benchmark.json"
        api_data = load_json(api_path)
    else:
        print("[3/4] API benchmark: SKIPPED")

    pipeline_data: dict[str, Any] = {}
    if not args.skip_pipeline:
        print(f"[4/4] Running pipeline benchmark ({args.pipeline_runs} runs)...")
        rc, output = run_python("benchmark_pipeline.py", [
            "--runs", str(args.pipeline_runs),
            "--output-dir", str(out_dir),
        ], timeout=args.pipeline_runs * 600)
        print(output)
        pipeline_path = out_dir / "pipeline_benchmark_detail.json"
        pipeline_data = load_json(pipeline_path)
    else:
        print("[4/4] Pipeline benchmark: SKIPPED")

    print(f"\n{'='*60}")
    print("Generating final report...")
    print(f"{'='*60}")

    metrics_table = build_metrics_table(pipeline_data, api_data, kafka_data, docker_stats)
    csv_path, json_path = write_report(metrics_table, out_dir)

    # Generate Markdown Analysis
    run_python("generate_analysis_md.py", [
        "--csv", str(csv_path),
        "--out", str(out_dir / "performance_analysis.md"),
    ])

    good = sum(1 for r in metrics_table if r["status"] == "good")
    acceptable = sum(1 for r in metrics_table if r["status"] == "acceptable")
    bad = sum(1 for r in metrics_table if r["status"] == "bad")

    print(f"\n  Total metrics: {len(metrics_table)}")
    print(f"  Good: {good}  Acceptable: {acceptable}  Bad: {bad}")
    print(f"  CSV report: {csv_path}")
    print(f"  JSON report: {json_path}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
