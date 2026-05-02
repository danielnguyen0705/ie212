# Frontend README

## 1. Tổng quan frontend

Đây là phần frontend của dashboard IE212, xây dựng bằng:

* React 19
* Vite
* TypeScript
* Tailwind CSS
* Recharts để hiển thị đồ thị
* React Router DOM để điều hướng client-side
* lucide-react cho icon

Frontend kết nối với backend API tại `http://localhost:8008` và hiển thị các lần chạy dự đoán, mã chứng khoán và các biểu đồ phân tích.

## 2. Cách chạy frontend

Từ thư mục gốc của dự án:

```bash
cd frontend
npm install
npm run dev
```

Sau đó mở trình duyệt:

```text
http://localhost:5173
```

Nếu backend chưa chạy, frontend vẫn sẽ khởi động, nhưng các yêu cầu dữ liệu sẽ lỗi khi gọi tới `http://localhost:8008`.

## 3. Dừng và khởi động lại frontend

### Dừng

Nếu server dev đang chạy, dùng:

```bash
Ctrl + C
```

Ở terminal chạy docker:
docker compose --env-file compose/.env -f compose/compose.yaml down

### Khởi động lại

Mở terminal để build docker:
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build

docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-triggerer

Từ thư mục `frontend`:

```bash
npm run dev
```


## 4. Kiến trúc frontend

### Điểm vào chính

* `frontend/src/App.tsx` định nghĩa các route của ứng dụng.
* `App.tsx` quản lý trạng thái run ID hiện tại và điều hướng đến:
  * `/` - Dashboard
  * `/analytics` - trang Analytics
  * `/ticker/:ticker` - trang chi tiết ticker

### Layout và điều hướng

* `frontend/src/components/Layout.tsx` xây dựng cấu trúc chính của trang với header và layout hai cột.
* `frontend/src/components/Header.tsx` chứa các nút điều hướng, kiểm tra API, refresh, copy run ID và mở API docs.

### Các trang

* `frontend/src/pages/PredictionTable.tsx` - bảng dự đoán với lọc và liên kết ticker.
* `frontend/src/pages/RecentRuns.tsx` - chọn run gần nhất.
* `frontend/src/pages/Analytics.tsx` - trang phân tích tổng hợp các biểu đồ và số liệu.
* `frontend/src/pages/TickerDetail.tsx` - trang chi tiết ticker với lịch sử giá và dự đoán.

### Thành phần biểu đồ / dữ liệu

* `frontend/src/components/Statistics.tsx` - các biểu đồ phân tích về phân phối lợi nhuận, phân phối độ tin cậy, tỷ lệ độ tin cậy và scatter plot.
* `frontend/src/components/RunSummary.tsx` - thẻ tóm tắt run trên dashboard.

### Luồng dữ liệu

* `App.tsx` lưu run ID đang chọn trong state của React.
* `PredictionTable` gọi `GET /predictions/runs/{run_id}` để lấy dự đoán cho run đã chọn.
* `RecentRuns` gọi `GET /predictions/runs/recent` và cập nhật run ID khi chọn một lần chạy mới.
* `RunSummary` gọi `GET /dashboard/summary` và tính toán top dự đoán tích cực/tiêu cực từ dữ liệu run gần nhất.
* `Statistics` gọi dữ liệu run đã chọn và hiển thị biểu đồ.
* `TickerDetail` gọi `GET /prices/ticker/{ticker}/history` và `GET /predictions/ticker/{ticker}/history`.

## 5. Tính năng frontend

### Điều hướng

* Thanh điều hướng trên cùng cho phép chuyển đổi giữa `Dashboard` và `Analytics`.
* Có thêm nút `Refresh` để tải lại trang, nút `Copy Run ID`, nút kiểm tra API và nút mở API Docs.

### Trang Dashboard

Trang Dashboard chính bao gồm:

* Bảng dự đoán
  * Hiển thị ticker, giá đóng cửa gần nhất, giá dự đoán, delta, lợi nhuận dự đoán, độ tin cậy và thời gian.
  * Có ô lọc để tìm ticker.
  * Mỗi ticker liên kết tới trang chi tiết ticker `/ticker/:ticker`.
* Tóm tắt run
  * Hiển thị run ID mới nhất, số lượng ticker, lợi nhuận dự đoán trung bình và thời gian cập nhật gần nhất.
  * Hiển thị các ticker dự đoán tốt nhất và dự đoán xấu nhất.
* Chọn run gần nhất
  * Tải metadata các run gần đây.
  * Nhấn vào run mới sẽ cập nhật run đang xem trên dashboard.

### Trang Analytics

Trang Analytics bao gồm:

* Các thẻ KPI cho tỷ lệ thắng, độ tin cậy trung bình, lợi nhuận lớn nhất và lợi nhuận nhỏ nhất.
* Các biểu đồ:
  * Phân phối lợi nhuận dự đoán
  * Phân phối độ tin cậy (Graph Gate)
  * Biểu đồ tròn phân bổ độ tin cậy
  * Biểu đồ scatter độ tin cậy theo độ lớn lợi nhuận
* Các bảng tóm tắt hiển thị ticker có độ tin cậy cao nhất và các dự đoán lợi nhuận tốt nhất/tồi nhất.

### Trang chi tiết ticker

Trang này cung cấp thông tin chi tiết theo ticker:

* Biểu đồ giá thực tế so với giá dự đoán.
* Lịch sử xu hướng dự đoán.
* Đường thời gian độ tin cậy.
* Thẻ tóm tắt với giá hiện tại, thay đổi giá, độ tin cậy mới nhất và lợi nhuận dự đoán.
* Nút export placeholder cho tải chart.

### Các tính năng tiện ích

* Sao chép run ID vào clipboard.
* Nút kiểm tra trạng thái API gọi `http://localhost:8008/health`.
* Liên kết nhanh tới Swagger docs backend tại `http://localhost:8008/docs`.

## 6. Các endpoint dữ liệu frontend

Frontend sử dụng các route backend tại `http://localhost:8008`:

* `GET /predictions/runs/{run_id}` - lấy dự đoán cho run được chọn
* `GET /predictions/runs/recent` - danh sách run gần nhất
* `GET /dashboard/summary` - số liệu tổng quan dashboard
* `GET /predictions/runs/latest` - dự đoán run mới nhất cho top positive/negative
* `GET /prices/ticker/{ticker}/history` - lịch sử giá ticker
* `GET /predictions/ticker/{ticker}/history` - lịch sử dự đoán ticker
* `GET /health` - kiểm tra trạng thái API
* `GET /docs` - tài liệu API / Swagger

## 7. Cấu trúc thư mục

```
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Layout.tsx
│   │   ├── RunSummary.tsx
│   │   └── Statistics.tsx
│   ├── pages/
│   │   ├── Analytics.tsx
│   │   ├── Dashboard.tsx
│   │   ├── PredictionTable.tsx
│   │   ├── RecentRuns.tsx
│   │   └── TickerDetail.tsx
│   └── main.tsx
└── public/
```

## 8. Ghi chú

* Frontend được thiết kế để hoạt động với backend local ở `http://localhost:8008`.
* Nếu backend không sẵn sàng, các thành phần dashboard sẽ hiển thị trạng thái đang tải hoặc lỗi.
* Dùng `npm run build` để kiểm tra TypeScript và Vite compile thành công.
