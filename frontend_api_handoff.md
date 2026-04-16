# Frontend API Handoff

## Project

IE212 Big Data Stock Prediction System

## Purpose

Tài liệu này dùng để bàn giao backend API cho frontend team để phát triển web dashboard mới.
Frontend **không cần đọc trực tiếp PostgreSQL** và **không cần đụng vào pipeline Airflow / Spark / Kafka / ML inference**.
Frontend chỉ cần gọi các REST API bên dưới.

---

## Base URL

### Local

```txt
http://localhost:8008
```

### Swagger Docs

```txt
http://localhost:8008/docs
```

## General Notes

- Tất cả API hiện tại là read-only
- Response format là JSON
- Thời gian trả về theo ISO format nếu có timestamp
- Khi resource không tồn tại, API trả `404`
- Frontend nên xử lý:
  - loading state
  - empty state
  - error state

## Recommended Frontend Mapping

### Dashboard Overview

Dùng:

- `GET /dashboard/summary`
- `GET /predictions/runs/recent`

### Prediction Table

Dùng:

- `GET /predictions/runs/latest`

### Run Detail

Dùng:

- `GET /predictions/runs/{run_id}`

### Ticker Dropdown / Filter

Dùng:

- `GET /tickers`

### Prediction History Chart by Ticker

Dùng:

- `GET /predictions/ticker/{ticker}/history?limit=30`

### Actual Price Mini Chart

Dùng:

- `GET /prices/ticker/{ticker}/history?days=30`

## API Endpoints

### 1. Health Check

**Endpoint**

`GET /health`

**Purpose**

Kiểm tra FastAPI và kết nối PostgreSQL có hoạt động không.

**Example Request**

```txt
http://localhost:8008/health
```

**Example Response**

```json
{
  "status": "ok",
  "database": true,
  "inference_predictions_table": true
}
```

**Frontend Usage**

- Có thể dùng cho trang System Status
- Có thể dùng để kiểm tra backend trước khi render dữ liệu chính

### 2. Get Available Tickers

**Endpoint**

`GET /tickers`

**Purpose**

Lấy danh sách tất cả ticker hiện có trong prediction database.

**Example Request**

```txt
http://localhost:8008/tickers
```

**Example Response**

```json
{
  "tickers": ["AAPL", "ADBE", "AMD", "CMCSA", "COST", "INTC", "INTU", "MSFT", "QCOM", "SBUX"]
}
```

**Frontend Usage**

- Dropdown chọn ticker
- Filter ticker trong prediction table
- Tabs cho ticker detail

### 3. Dashboard Summary

**Endpoint**

`GET /dashboard/summary`

**Purpose**

Lấy thông tin tổng quan của latest run để hiển thị overview cards trên dashboard.

**Example Request**

```txt
http://localhost:8008/dashboard/summary
```

**Example Response**

```json
{
  "latest_run_id": "local_inference_20260416_004254",
  "model_name": "hybrid_expanding_best_full",
  "as_of_date": "2023-12-29",
  "row_count": 10,
  "ticker_count": 10,
  "avg_pred_return": -0.00027538560262234477,
  "max_pred_return": -6.3801746337016915e-6,
  "min_pred_return": -0.00085997235502176617,
  "last_updated": "2026-04-16T00:42:54.272119+00:00"
}
```

**Field Meanings**

- `latest_run_id`: ID của run mới nhất
- `model_name`: tên model dùng để dự đoán
- `as_of_date`: ngày dữ liệu dự báo
- `row_count`: số bản ghi prediction trong latest run
- `ticker_count`: số lượng ticker
- `avg_pred_return`: trung bình predicted return
- `max_pred_return`: predicted return lớn nhất
- `min_pred_return`: predicted return nhỏ nhất
- `last_updated`: thời gian ghi prediction gần nhất

**Frontend Usage**

- KPI cards
- Overview section
- Header thông tin latest run

### 4. Get Latest Prediction Run

**Endpoint**

`GET /predictions/runs/latest`

**Purpose**

Lấy toàn bộ dữ liệu prediction của latest run.

**Example Request**

```txt
http://localhost:8008/predictions/runs/latest
```

**Example Response**

```json
{
  "run_id": "local_inference_20260416_004254",
  "as_of_date": "2023-12-29",
  "model_name": "hybrid_expanding_best_full",
  "row_count": 10,
  "items": [
    {
      "ticker": "AAPL",
      "last_close": 192.52999877929688,
      "pred_close": 192.52574157714844,
      "pred_return": -0.000022111889967431326,
      "graph_gate": 0.0,
      "created_at": "2026-04-16T00:42:54.272119+00:00"
    },
    {
      "ticker": "ADBE",
      "last_close": 596.5999755859375,
      "pred_close": 596.5957641601562,
      "pred_return": -0.00007459044508196369,
      "graph_gate": 0.0,
      "created_at": "2026-04-16T00:42:54.272119+00:00"
    }
  ]
}
```

**Field Meanings**

Root fields:

- `run_id`: ID của prediction run
- `as_of_date`: ngày dữ liệu dự báo
- `model_name`: tên model
- `row_count`: số ticker trong run
- `items`: danh sách prediction per ticker

Item fields:

- `ticker`: mã cổ phiếu
- `last_close`: giá close gần nhất trước ngày dự báo
- `pred_close`: giá close dự báo
- `pred_return`: tỷ lệ thay đổi dự báo
- `graph_gate`: hệ số gate của graph branch nếu có
- `created_at`: thời điểm record được lưu vào DB

**Frontend Usage**

- Prediction table chính
- Sort / search / filter theo ticker
- Hiển thị màu tăng giảm theo `pred_return`

### 5. Get Recent Runs

**Endpoint**

`GET /predictions/runs/recent`

**Query Parameters**

- `limit` (optional, default = 10)

**Example Request**

```txt
http://localhost:8008/predictions/runs/recent
```

**Example Response**

```json
{
  "count": 3,
  "items": [
    {
      "run_id": "local_inference_20260416_004254",
      "as_of_date": "2023-12-29",
      "model_name": "hybrid_expanding_best_full",
      "row_count": 10,
      "first_created_at": "2026-04-16T00:42:54.272119+00:00",
      "last_created_at": "2026-04-16T00:42:54.272119+00:00"
    },
    {
      "run_id": "local_inference_20260415_161956",
      "as_of_date": "2023-12-29",
      "model_name": "hybrid_expanding_best_full",
      "row_count": 10,
      "first_created_at": "2026-04-15T16:19:56.962258+00:00",
      "last_created_at": "2026-04-15T16:19:56.962258+00:00"
    }
  ]
}
```

**Frontend Usage**

- Recent runs list
- Sidebar runs
- Run history cards
- Cho phép click vào run để mở chi tiết

### 6. Get Run Detail by Run ID

**Endpoint**

`GET /predictions/runs/{run_id}`

**Path Parameter**

- `run_id`: ID của run muốn xem

**Example Request**

```txt
http://localhost:8008/predictions/runs/local_inference_20260416_004254
```

**Example Response**

```json
{
  "run_id": "local_inference_20260416_004254",
  "as_of_date": "2023-12-29",
  "model_name": "hybrid_expanding_best_full",
  "row_count": 10,
  "items": [
    {
      "ticker": "AAPL",
      "last_close": 192.52999877929688,
      "pred_close": 192.52574157714844,
      "pred_return": -0.000022111889967431326,
      "graph_gate": 0.0,
      "created_at": "2026-04-16T00:42:54.272119+00:00"
    }
  ]
}
```

**Frontend Usage**

- Run detail page
- Modal xem chi tiết từng run
- So sánh latest run với run cũ

**Error Example**

```json
{
  "detail": "Run id not found: invalid_run_id"
}
```

### 7. Get Latest Predictions Alias

**Endpoint**

`GET /predictions/latest`

**Purpose**

API alias của latest run prediction.
Có thể dùng thay cho `/predictions/runs/latest`, nhưng frontend nên ưu tiên `/predictions/runs/latest` để naming nhất quán hơn.

**Example Request**

```txt
http://localhost:8008/predictions/latest
```

**Frontend Recommendation**

Ưu tiên dùng:

- `GET /predictions/runs/latest`

### 8. Get Prediction History by Ticker

**Endpoint**

`GET /predictions/ticker/{ticker}/history`

**Path Parameter**

- `ticker`: mã cổ phiếu

**Query Parameters**

- `limit` (optional, default = 30)

**Example Request**

```txt
http://localhost:8008/predictions/ticker/AAPL/history
```

**Example Response**

```json
{
  "ticker": "AAPL",
  "items": [
    {
      "run_id": "local_inference_20260416_004254",
      "as_of_date": "2023-12-29",
      "last_close": 192.52999877929688,
      "pred_close": 192.52574157714844,
      "pred_return": -0.000022111889967431326,
      "graph_gate": 0.0,
      "model_name": "hybrid_expanding_best_full",
      "created_at": "2026-04-16T00:42:54.272119+00:00"
    },
    {
      "run_id": "local_inference_20260415_161956",
      "as_of_date": "2023-12-29",
      "last_close": 192.52999877929688,
      "pred_close": 192.52574157714844,
      "pred_return": -0.000022111889967431326,
      "graph_gate": 0.0,
      "model_name": "hybrid_expanding_best_full",
      "created_at": "2026-04-15T16:19:56.962258+00:00"
    }
  ]
}
```

**Frontend Usage**

- Prediction history line chart
- Ticker detail page
- Hiển thị `pred_close` / `pred_return` theo từng run

**Error Example**

```json
{
  "detail": "No prediction history found for ticker: XYZ"
}
```

### 9. Get Actual Price History by Ticker

**Endpoint**

`GET /prices/ticker/{ticker}/history`

**Path Parameter**

- `ticker`: mã cổ phiếu

**Query Parameters**

- `days` (optional, default = 30)

**Example Request**

```txt
http://localhost:8008/prices/ticker/AAPL/history
```

**Example Response**

```json
{
  "ticker": "AAPL",
  "days": 30,
  "items": [
    {
      "date": "2023-11-16",
      "close": 189.7100067138672
    },
    {
      "date": "2023-11-17",
      "close": 189.69000244140625
    },
    {
      "date": "2023-11-20",
      "close": 191.4499969482422
    }
  ]
}
```

**Frontend Usage**

- Mini chart 1 tháng
- Actual price line chart
- So sánh actual chart với prediction chart

**Error Example**

```json
{
  "detail": "Raw CSV not found for ticker: XYZ"
}
```

## Suggested Frontend Screens

### 1. Dashboard Overview

Use:

- `GET /dashboard/summary`
- `GET /predictions/runs/recent`

Show:

- Latest Run ID
- Model Name
- As Of Date
- Row Count
- Ticker Count
- Last Updated
- Recent Runs

### 2. Prediction Table

Use:

- `GET /predictions/runs/latest`

Show:

- `ticker`
- `last_close`
- `pred_close`
- `pred_return`
- `graph_gate`

Features:

- search ticker
- filter ticker
- sort by predicted return
- color positive/negative return

### 3. Run Detail Page

Use:

- `GET /predictions/runs/{run_id}`

Show:

- run metadata
- all prediction items in that run
- charts or summary for selected run

### 4. Ticker Detail Page

Use:

- `GET /predictions/ticker/{ticker}/history`
- `GET /prices/ticker/{ticker}/history`

Show:

- ticker name
- actual price history
- prediction history
- latest predicted close
- latest predicted return
- graph gate value if available

## Suggested Frontend Data Handling

### Recommended Types

**Prediction Item**

```ts
type PredictionItem = {
  ticker: string;
  last_close: number;
  pred_close: number;
  pred_return: number | null;
  graph_gate: number | null;
  created_at: string | null;
};
```

**Latest Run Response**

```ts
type LatestRunResponse = {
  run_id: string;
  as_of_date: string | null;
  model_name: string;
  row_count: number;
  items: PredictionItem[];
};
```

**Recent Run Item**

```ts
type RecentRunItem = {
  run_id: string;
  as_of_date: string | null;
  model_name: string;
  row_count: number;
  first_created_at: string | null;
  last_created_at: string | null;
};
```

**Dashboard Summary**

```ts
type DashboardSummary = {
  latest_run_id: string;
  model_name: string;
  as_of_date: string | null;
  row_count: number;
  ticker_count: number;
  avg_pred_return: number | null;
  max_pred_return: number | null;
  min_pred_return: number | null;
  last_updated: string | null;
};
```

**Price History Item**

```ts
type PriceHistoryItem = {
  date: string;
  close: number;
};
```

**Prediction History Item**

```ts
type PredictionHistoryItem = {
  run_id: string;
  as_of_date: string | null;
  last_close: number;
  pred_close: number;
  pred_return: number | null;
  graph_gate: number | null;
  model_name: string | null;
  created_at: string | null;
};
```

## Notes for Frontend Team

- `pred_return` có thể âm hoặc dương
- `graph_gate` hiện có thể là `0.0` với nhiều ticker
- Không nên giả định field nào luôn luôn khác `null`
- Nên format number khi hiển thị:
  - price: 2-4 chữ số thập phân
  - return: phần trăm hoặc decimal tùy UI
- Nên hiển thị thời gian theo local timezone của browser nếu cần

## Error Handling Recommendations

Frontend nên xử lý các trường hợp:

- API chưa sẵn sàng
- DB tạm thời lỗi
- `404` khi ticker không tồn tại
- `404` khi run id không tồn tại
- `items` rỗng

Suggested UI:

- loading spinner
- `No data available`
- `Ticker not found`
- retry button

## Final Recommendation

Frontend nên bắt đầu từ flow sau:

1. load `/dashboard/summary`
2. load `/tickers`
3. load `/predictions/runs/latest`
4. render dashboard overview + prediction table
5. sau đó mới thêm:
   - recent runs
   - run detail
   - ticker detail
   - charts
