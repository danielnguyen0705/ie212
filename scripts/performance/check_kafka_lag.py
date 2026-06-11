from __future__ import annotations

import argparse
import json
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("outputs/performance")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_topic_offsets(container: str = "ie212-kafka", bootstrap: str = "localhost:9092", topic: str = "stock-price") -> dict[str, Any]:
    cmd = [
        "docker", "exec", container,
        "/opt/kafka/bin/kafka-run-class.sh", "kafka.tools.GetOffsetShell",
        "--bootstrap-server", bootstrap,
        "--topic", topic,
        "--time", "-1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    if proc.returncode != 0:
        return {"error": stderr.strip(), "timestamp": utc_now()}

    partitions: list[dict[str, Any]] = []
    total_offset = 0
    for line in stdout.strip().splitlines():
        match = re.match(r"^(\S+):(\d+):(\d+)$", line.strip())
        if match:
            partition = int(match.group(2))
            offset = int(match.group(3))
            partitions.append({"partition": partition, "log_end_offset": offset})
            total_offset += offset

    return {
        "timestamp": utc_now(),
        "topic": topic,
        "partitions": partitions,
        "total_messages": total_offset,
    }


def get_consumer_group_lag(container: str, bootstrap: str, group: str) -> dict[str, Any]:
    cmd = [
        "docker", "exec", container,
        "/opt/kafka/bin/kafka-consumer-groups.sh",
        "--bootstrap-server", bootstrap,
        "--describe",
        "--group", group,
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    if proc.returncode != 0:
        return {"error": stderr.strip(), "group": group}
    return {"group": group, "raw_output": stdout.strip(), "timestamp": utc_now()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Kafka topic offsets and optional consumer group lag.")
    parser.add_argument("--container", default="ie212-kafka")
    parser.add_argument("--bootstrap-server", default="localhost:9092")
    parser.add_argument("--topic", default="stock-price")
    parser.add_argument("--group", default="", help="Consumer group to inspect (optional)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    result = get_topic_offsets(args.container, args.bootstrap_server, args.topic)

    if args.group:
        result["consumer_group"] = get_consumer_group_lag(args.container, args.bootstrap_server, args.group)

    out_path = Path(args.output_dir) / "kafka_offsets.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
