# IE212 Big Data Architecture — Performance Evaluation Guide

## Tổng quan

Module này đo hiệu năng kiến trúc Big Data, không đo chất lượng mô hình ML. Mục tiêu là chứng minh rằng pipeline end-to-end (Kafka → Spark → MinIO → ML Inference → PostgreSQL → FastAPI) hoạt động đúng và đủ nhanh.

## Cấu trúc file

```
scripts/performance/
├── run_performance_suite.py    # Orchestrator: chạy tất cả benchmark và sinh report
├── benchmark_pipeline.py       # Đo E2E latency, success rate, data completeness, throughput
├── benchmark_api.py            # Đo FastAPI response time + throughput
├── collect_docker_stats.py     # Đo CPU/RAM usage qua docker stats
├── check_kafka_lag.py          # Đo Kafka topic offset, consumer lag (Python)
└── check_kafka_lag.sh          # Đo Kafka offset qua shell script

outputs/performance/
├── performance_report.csv      # Bảng tổng hợp tất cả metric
├── performance_summary.json    # JSON đầy đủ với status và note
├── pipeline_benchmark_detail.json  # Chi tiết từng lần chạy pipeline
├── api_benchmark.json          # Chi tiết benchmark API endpoints
├── docker_stats.csv            # CPU/RAM snapshot theo thời gian
├── docker_stats.json           # Docker stats dạng JSON
└── kafka_offsets.json          # Kafka topic offset info
```

## Điều kiện tiên quyết

1. Docker Compose stack đang chạy: `docker ps` phải thấy các container `ie212-*`
2. Các container cần thiết: `ie212-kafka`, `ie212-spark-master`, `ie212-ml-infer`, `ie212-fastapi`, `ie212-postgres`, `ie212-minio`, `ie212-stock-producer`
3. Python 3.11+ với `psycopg2-binary` được cài (có trong `requirements.txt`)

Khởi động stack nếu chưa chạy:
```bash
cd compose
docker compose up -d
```

## Cách chạy benchmark

### 1. Chạy toàn bộ benchmark bằng 1 lệnh duy nhất (khuyến nghị)

Từ thư mục gốc project `D:\ie212`, chạy:

```powershell
scripts\performance\run_all_performance.bat
```

Lệnh này tự dùng `.venv\Scripts\python.exe` nếu có, rồi đo toàn bộ chỉ số chính:
- Docker CPU/RAM usage
- Kafka offset/lag status
- FastAPI response time và throughput
- End-to-end pipeline latency
- Spark job runtime
- Kafka/Spark/API throughput
- Pipeline success rate
- Data completeness

Output được sinh tại:
- `outputs/performance/performance_report.csv`
- `outputs/performance/performance_summary.json`
- `outputs/performance/performance_analysis.md`
- `outputs/performance/pipeline_benchmark_detail.json`
- `outputs/performance/api_benchmark.json`
- `outputs/performance/docker_stats.csv`
- `outputs/performance/kafka_offsets.json`

Nếu muốn chỉnh số lần chạy, dùng lệnh đầy đủ:

```powershell
.venv\Scripts\python.exe scripts\performance\run_performance_suite.py --pipeline-runs 1 --api-iterations 5 --docker-stats-samples 2 --output-dir outputs\performance
```

**Chú ý:** Mỗi lần chạy pipeline mất khoảng 1–5 phút tùy máy và cache Spark/Maven.

### 2. Chạy từng phần riêng lẻ nếu cần debug riêng metric nào đó

#### Chỉ benchmark API
```bash
python scripts/performance/benchmark_api.py \
  --iterations 20 \
  --base-url http://localhost:8008 \
  --output-dir outputs/performance
```

#### Chỉ thu thập Docker stats (CPU/RAM)
```bash
python scripts/performance/collect_docker_stats.py \
  --samples 5 \
  --interval-seconds 10 \
  --output-dir outputs/performance
```

#### Chỉ kiểm tra Kafka offset
```bash
python scripts/performance/check_kafka_lag.py \
  --container ie212-kafka \
  --bootstrap-server localhost:9092 \
  --topic stock-price \
  --output-dir outputs/performance
```

#### Kiểm tra Kafka qua shell (trong container)
```bash
bash scripts/performance/check_kafka_lag.sh
# Hoặc với consumer group cụ thể:
GROUP=my-group bash scripts/performance/check_kafka_lag.sh
```

#### Chỉ chạy pipeline benchmark
```bash
python scripts/performance/benchmark_pipeline.py \
  --runs 5 \
  --output-dir outputs/performance
```

### 3. Skip một số phần

```bash
# Chỉ API + docker stats, bỏ qua pipeline (chạy nhanh hơn)
python scripts/performance/run_performance_suite.py \
  --skip-pipeline \
  --api-iterations 20 \
  --docker-stats-samples 5
```

## Cách đọc kết quả

### performance_report.csv

Bảng chứa tất cả metric. Các cột:

| Cột | Ý nghĩa |
|---|---|
| `metric_name` | Tên chỉ số |
| `component` | Thành phần (kafka, spark, fastapi, pipeline, container name) |
| `value` | Giá trị đo được |
| `unit` | Đơn vị (seconds, percent, msg/s, rec/s, bytes) |
| `status` | `good` / `acceptable` / `bad` |
| `note` | Ghi chú thêm |

### performance_summary.json

```json
{
  "generated_at": "2026-06-10T...",
  "total_metrics": 42,
  "status_counts": {
    "good": 35,
    "acceptable": 5,
    "bad": 2
  },
  "metrics": [...]
}
```

### pipeline_benchmark_detail.json

Chi tiết từng lần chạy pipeline với timestamps của từng bước và metrics:
- `total_duration_s`: Thời gian E2E
- `messages_produced`: Số tin nhắn Kafka đã gửi
- `kafka_batch_rows`: Số record trong `stock.kafka_ticks_batch`
- `prediction_rows`: Số prediction trong `stock.inference_predictions`
- `data_completeness_pct`: `prediction_rows / 10 * 100` (10 tickers)
- `step_metrics`: Duration từng bước trong pipeline

## Các chỉ số được đo

### Ngưỡng đánh giá

| Metric | Good | Acceptable | Bad |
|---|---|---|---|
| API response time | < 500ms | < 1s | ≥ 1s |
| Pipeline success rate | ≥ 90% | ≥ 70% | < 70% |
| Data completeness | ≥ 99% | ≥ 90% | < 90% |
| E2E pipeline latency | < 120s | < 300s | ≥ 300s |
| CPU usage per container | < 80% | < 95% | ≥ 95% |
| Memory usage per container | < 80% | < 95% | ≥ 95% |
| Kafka topic has messages | > 0 | — | = 0 |
| Kafka consumer lag | 0 | — | > 0 |

### Chỉ số theo từng thành phần

#### 1. End-to-End Latency
- **Đo trong:** `benchmark_pipeline.py`
- **Phương pháp:** `time.perf_counter()` bao quanh toàn bộ pipeline gồm 7 bước
- **Timestamps ghi lại:** `pipeline_start`, `{step}_start`, `{step}_end`, `pipeline_end`
- **Metric name trong CSV:** `end_to_end_latency`

#### 2. Spark Job Runtime
- **Đo trong:** `benchmark_pipeline.py` → `step_metrics`
- **Bước:** `spark_batch_to_postgres`, `spark_batch_to_parquet`
- **Metric names:** `step_duration_spark_batch_to_postgres`, `step_duration_spark_batch_to_parquet`
- **Ghi lại:** duration_s, return_code, success

#### 3. Kafka Consumer Lag
- **Đo trong:** `check_kafka_lag.py`
- **Phương pháp:** `kafka-run-class.sh GetOffsetShell` để đọc log-end-offset
- **Ghi chú:** Project này không dùng persistent consumer group vì Spark batch đọc theo `startingOffsets: earliest` và `endingOffsets: latest`. Nghĩa là Spark luôn đọc toàn bộ topic mỗi lần chạy. Không có consumer lag theo nghĩa truyền thống. Kết quả hiển thị là `0` với status `good`.
- **Nếu muốn test consumer group thật:** Cần dùng `kafka-console-consumer.sh` với `--group` hoặc Spark streaming với consumer group cố định.

#### 4. Throughput
- **Kafka producer throughput:** `messages_produced / publish_step_duration_s` (msg/s)
- **Spark processing throughput:** `kafka_batch_rows / total_spark_duration_s` (rec/s)
- **API throughput:** `1 / avg_response_time_s * iterations` (req/s)
- **Metric names:** `kafka_producer_throughput`, `spark_processing_throughput`, `api_throughput_*`

#### 5. CPU/RAM Usage
- **Đo trong:** `collect_docker_stats.py`
- **Phương pháp:** `docker stats --no-stream` snapshot
- **Containers được đo:** postgres, minio, kafka, stock-producer, spark-master, spark-worker, airflow-apiserver, airflow-scheduler, ml-infer, fastapi
- **Output:** `docker_stats.csv`, `docker_stats.json`

#### 6. Pipeline Success Rate
- **Đo trong:** `benchmark_pipeline.py`
- **Phương pháp:** Chạy N lần pipeline, đếm thành công / thất bại
- **Metric name:** `pipeline_success_rate` (đơn vị: %)

#### 7. Data Completeness
- **Đo trong:** `benchmark_pipeline.py`
- **Công thức:** `prediction_rows / 10 * 100` (có 10 tickers)
- **Input records:** Số messages Kafka (offset_after - offset_before)
- **Output records:** Số rows trong `stock.inference_predictions` của run mới nhất
- **Metric name:** `data_completeness`

#### 8. FastAPI Response Time
- **Đo trong:** `benchmark_api.py`
- **Endpoints đo:** `/health`, `/`, `/tickers`, `/dashboard/summary`, `/predictions/runs/latest`, `/predictions/runs/recent`
- **Thống kê:** avg, min, max, median, p95 response time + throughput (req/s)

## Đọc Airflow DAG runtime

Airflow không expose DAG runtime qua API trong phiên bản này. Cách đọc:

1. **Airflow UI:** Truy cập `http://localhost:8088` → `DAGs` → `ie212_kafka_to_inference_pipeline` → Click vào run → xem `Duration`
2. **Airflow CLI (trong container):**
   ```bash
   docker exec ie212-airflow-apiserver airflow dags list-runs -d ie212_kafka_to_inference_pipeline --output table
   ```
3. **Query trực tiếp PostgreSQL airflow_meta:**
   ```sql
   SELECT dag_id, run_id, state, start_date, end_date, (end_date - start_date) AS duration
   FROM airflow_meta.dag_run
   WHERE dag_id = 'ie212_kafka_to_inference_pipeline'
   ORDER BY start_date DESC
   LIMIT 10;
   ```
   Kết nối: `localhost:15432`, database `airflow_meta`, user `stock_user`, password `change_me_postgres`

## Spark UI

Xem Spark job history và duration tại `http://localhost:8080` (Spark Master UI).
- Click vào Application để xem duration, executor memory, records processed.

## Các chỉ số chứng minh kiến trúc Big Data tốt

| Chỉ số | Chứng minh điều gì |
|---|---|
| `data_completeness ≥ 99%` | Kafka → Spark → DB không mất dữ liệu |
| `pipeline_success_rate ≥ 90%` | Pipeline ổn định, các component không gây lỗi nhau |
| `end_to_end_latency < 120s` | Kiến trúc đủ nhanh cho use case near-realtime |
| `kafka_producer_throughput > 1 msg/s` | Kafka ingest đủ nhanh |
| `spark_processing_throughput > 1 rec/s` | Spark xử lý không phải bottleneck |
| `api_response_time_health < 0.5s` | API layer responsive |
| `cpu_usage < 80%` | Tài nguyên không bị saturate |
| `kafka_topic_total_messages > 0` | Kafka nhận dữ liệu thành công |

## Lưu ý về Kafka consumer lag

Dự án này không có Kafka consumer group thật vì Spark batch đọc Kafka dạng "snapshot" (earliest → latest offset tại thời điểm chạy). Đây là thiết kế đúng cho batch processing. Consumer lag = 0 không phải vì chưa đọc, mà vì không có consumer group persistent nào cần track.

Nếu muốn có streaming consumer group (để theo dõi lag thật sự), cần dùng `write_kafka_stream_to_postgres.py` thay cho batch mode, và Spark Structured Streaming sẽ tạo consumer group với prefix `spark-`.

## Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|---|---|---|
| `NoBrokersAvailable` | Kafka chưa ready | `docker compose up kafka -d && sleep 30` |
| `psycopg2.OperationalError` | Postgres chưa ready hoặc sai port | Kiểm tra port `15432`: `docker ps` |
| Spark job timeout | Maven download chậm (lần đầu) | Chạy lại sau khi dependencies đã cache |
| `No parquet files found in MinIO` | Chưa chạy Spark batch → parquet | Chạy bước Spark trước MinIO sync |
| API `Connection refused` | FastAPI container chưa chạy | `docker compose up fastapi -d` |
