from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://localhost:8008"
DEFAULT_OUT_DIR = Path("outputs/performance")

ENDPOINTS = [
    {"method": "GET", "path": "/health", "name": "health"},
    {"method": "GET", "path": "/", "name": "root"},
    {"method": "GET", "path": "/tickers", "name": "tickers"},
    {"method": "GET", "path": "/dashboard/summary", "name": "dashboard_summary"},
    {"method": "GET", "path": "/predictions/runs/latest", "name": "predictions_latest"},
    {"method": "GET", "path": "/predictions/runs/recent?limit=5", "name": "predictions_recent"},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def benchmark_endpoint(base_url: str, endpoint: dict[str, str], iterations: int) -> dict[str, Any]:
    url = base_url.rstrip("/") + endpoint["path"]
    latencies: list[float] = []
    errors: list[str] = []
    status_codes: list[int] = []

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            req = urllib.request.Request(url, method=endpoint["method"])
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
                status_codes.append(resp.status)
                latencies.append(time.perf_counter() - start)
        except urllib.error.HTTPError as exc:
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            status_codes.append(exc.code)
            errors.append(f"HTTP {exc.code}")
        except Exception as exc:
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            status_codes.append(0)
            errors.append(str(exc))

    result: dict[str, Any] = {
        "endpoint": endpoint["path"],
        "name": endpoint["name"],
        "method": endpoint["method"],
        "iterations": iterations,
        "success_count": sum(1 for s in status_codes if 200 <= s < 400),
        "error_count": sum(1 for s in status_codes if s < 200 or s >= 400),
    }

    if latencies:
        result["avg_response_time_s"] = round(statistics.mean(latencies), 6)
        result["min_response_time_s"] = round(min(latencies), 6)
        result["max_response_time_s"] = round(max(latencies), 6)
        result["median_response_time_s"] = round(statistics.median(latencies), 6)
        result["p95_response_time_s"] = round(sorted(latencies)[int(len(latencies) * 0.95)], 6) if len(latencies) >= 2 else result["max_response_time_s"]
        result["throughput_rps"] = round(len(latencies) / sum(latencies), 2) if sum(latencies) > 0 else 0
    if errors:
        result["errors"] = errors[:5]

    return result


def evaluate_status(avg_time: float) -> str:
    if avg_time < 0.5:
        return "good"
    if avg_time < 1.0:
        return "acceptable"
    return "bad"


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark FastAPI endpoints for IE212.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    for ep in ENDPOINTS:
        res = benchmark_endpoint(args.base_url, ep, args.iterations)
        res["status"] = evaluate_status(res.get("avg_response_time_s", 999))
        results.append(res)
        print(f"  {ep['name']:25s} avg={res.get('avg_response_time_s', 'N/A'):.4f}s  status={res['status']}")

    out_path = Path(args.output_dir) / "api_benchmark.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": utc_now(), "base_url": args.base_url, "results": results}, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
