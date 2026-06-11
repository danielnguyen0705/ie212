from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("outputs/performance")
DEFAULT_CONTAINERS = [
    "ie212-postgres",
    "ie212-minio",
    "ie212-kafka",
    "ie212-stock-producer",
    "ie212-spark-master",
    "ie212-spark-worker",
    "ie212-airflow-apiserver",
    "ie212-airflow-scheduler",
    "ie212-ml-infer",
    "ie212-fastapi",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(cmd: list[str], timeout: int | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    return proc.returncode, stdout, stderr


def parse_docker_stats_line(line: str) -> dict[str, Any]:
    parts = line.split(",")
    if len(parts) != 5:
        raise ValueError(f"Unexpected docker stats format: {line}")
    name, cpu_percent, mem_usage, mem_percent, net_io = [p.strip() for p in parts]
    used_mem = mem_usage.split("/")[0].strip() if "/" in mem_usage else mem_usage
    return {
        "timestamp": utc_now(),
        "container": name,
        "cpu_percent": float(cpu_percent.replace("%", "").strip() or 0),
        "memory_usage": used_mem,
        "memory_percent": float(mem_percent.replace("%", "").strip() or 0),
        "net_io": net_io,
    }


def collect_once(containers: list[str]) -> list[dict[str, Any]]:
    cmd = [
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}}",
        *containers,
    ]
    rc, stdout, stderr = run_command(cmd, timeout=60)
    if rc != 0:
        raise RuntimeError(stderr.strip() or stdout.strip())
    rows = []
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            rows.append(parse_docker_stats_line(line))
    return rows


def write_rows(rows: list[dict[str, Any]], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["timestamp", "container", "cpu_percent", "memory_usage", "memory_percent", "net_io"]
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect docker stats snapshots for IE212 containers.")
    parser.add_argument("--samples", type=int, default=1, help="Number of snapshots to collect")
    parser.add_argument("--interval-seconds", type=float, default=5.0, help="Sleep between snapshots")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--containers", nargs="*", default=DEFAULT_CONTAINERS)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for idx in range(args.samples):
        rows.extend(collect_once(args.containers))
        if idx < args.samples - 1:
            time.sleep(args.interval_seconds)

    out_dir = Path(args.output_dir)
    write_rows(rows, out_dir / "docker_stats.csv", out_dir / "docker_stats.json")
    print(json.dumps({"rows": len(rows), "csv": str(out_dir / "docker_stats.csv")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
