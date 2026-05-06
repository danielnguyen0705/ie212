# Báo Cáo Triển Khai Frontend Dashboard IE212

## 1. Tổng Quan Dự Án

Dự án IE212 là hệ thống dự đoán giá chứng khoán sử dụng machine learning với kiến trúc microservices. Dự án bao gồm:

- **Backend Services**: API FastAPI, Inference service, PostgreSQL, Kafka, MinIO, Spark, Airflow
- **Frontend Dashboard**: React TypeScript application để visualize predictions và analytics
- **Data Pipeline**: Airflow DAGs cho ETL và inference workflows
- **Models**: Hybrid LSTM + Graph Neural Network cho stock prediction

Frontend dashboard được xây dựng bằng React 19, TypeScript, Vite, Tailwind CSS, và Recharts để cung cấp giao diện trực quan cho việc theo dõi và phân tích dự đoán giá chứng khoán.

## 2. Kiến Trúc Tổng Quan

### 2.1. Kiến Trúc Hệ Thống

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Inference     │
│   Dashboard     │◄──►│   (FastAPI)     │◄──►│   Service       │
│   (React)       │    │                 │    │   (PyTorch)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Kafka       │    │     MinIO       │
│   (Predictions) │    │   (Streaming)   │    │   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         └───────────────────────┼───────────────────────┘
                         Airflow DAGs
                     (Data Pipeline Orchestration)
```

### 2.2. Luồng Dữ Liệu

1. **Data Ingestion**: Producer service thu thập dữ liệu chứng khoán qua Kafka
2. **ETL Pipeline**: Airflow DAGs xử lý dữ liệu và lưu vào PostgreSQL/MinIO
3. **Model Training**: Spark jobs train models và lưu checkpoints
4. **Inference**: Inference service load model và generate predictions
5. **API Serving**: FastAPI expose predictions qua REST endpoints
6. **Visualization**: Frontend consume API và display charts/tables

## 3. Cách Khởi Động Dự Án

### 3.1. Yêu Cầu Hệ Thống

**Phần cứng:**
- RAM: Tối thiểu 8GB, khuyến nghị 16GB+
- CPU: 4 cores trở lên
- Disk: 20GB dung lượng trống

**Phần mềm:**
- Docker Desktop 4.0+
- Node.js 18+
- npm 8+
- Git
- Python 3.9+ (cho backend services)

### 3.2. Chuẩn Bị Môi Trường

#### Bước 1: Clone Repository
```bash
git clone <repository-url>
cd ie212
```

#### Bước 2: Cấu Hình Environment Variables
```bash
# Copy file .env mẫu
cp compose/.env.example compose/.env

# Chỉnh sửa các biến môi trường cần thiết
# POSTGRES_PASSWORD, KAFKA settings, MINIO credentials, etc.
```

#### Bước 3: Khởi Động Backend Services
```bash
# Khởi động infrastructure (PostgreSQL, Kafka, MinIO, Spark)
docker compose --env-file compose/.env -f compose/compose.yaml up -d postgres kafka minio spark-master spark-worker

# Khởi động producer để tạo dữ liệu mẫu
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build

# Khởi động Airflow cho data pipelines
docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-init
docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer
```

#### Bước 4: Khởi Động Inference và API Services
```bash
# Khởi động inference service
docker compose --env-file compose/.env -f compose/compose.yaml up -d inference

# Khởi động FastAPI backend
docker compose --env-file compose/.env -f compose/compose.yaml up -d api
```

#### Bước 5: Khởi Động Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

#### Bước 6: Truy Cập Ứng Dụng
Mở trình duyệt và truy cập: `http://localhost:5173`

### 3.3. Kiểm Tra Hoạt Động

#### Kiểm tra Backend Services:
```bash
# Health check API
curl http://localhost:8008/health

# Kiểm tra API docs
open http://localhost:8008/docs
```

#### Kiểm tra Frontend:
- Dashboard load thành công
- Có thể chọn run gần nhất
- Bảng dự đoán hiển thị dữ liệu
- Analytics charts render đúng
- Ticker detail pages hoạt động

## 4. Cách Tái Khởi Động Dự Án

### 4.1. Dừng Tất Cả Services
```bash
# Từ thư mục gốc dự án
docker compose --env-file compose/.env -f compose/compose.yaml down

# Dừng frontend (Ctrl + C trong terminal frontend)
```

### 4.2. Khởi Động Lại
```bash
# Khởi động backend services
docker compose --env-file compose/.env -f compose/compose.yaml up -d postgres kafka minio spark-master spark-worker
docker compose --env-file compose/.env -f compose/compose.yaml --profile producer up -d --build
docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-init
docker compose --env-file compose/.env -f compose/compose.yaml up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer
docker compose --env-file compose/.env -f compose/compose.yaml up -d inference api

# Khởi động frontend
cd frontend
npm run dev
```

### 4.3. Restart Riêng Lẻ Services
```bash
# Restart API service
docker compose --env-file compose/.env -f compose/compose.yaml restart api

# Restart inference service
docker compose --env-file compose/.env -f compose/compose.yaml restart inference

# Restart frontend (Ctrl + C rồi npm run dev lại)
```

## 5. Kiến Trúc Frontend

### 5.1. Công Nghệ Sử Dụng

- **React 19**: Framework UI với hooks và concurrent features
- **TypeScript**: Type safety và developer experience
- **Vite**: Build tool nhanh với HMR
- **Tailwind CSS**: Utility-first CSS framework
- **React Router DOM**: Client-side routing
- **Recharts**: Chart library cho data visualization
- **Lucide React**: Icon library

### 5.2. Cấu Trúc Thư Mục Frontend

```
frontend/
├── eslint.config.js              # ESLint configuration
├── index.html                    # HTML template
├── package.json                  # Dependencies và scripts
├── tsconfig.app.json             # TypeScript config cho app
├── tsconfig.json                 # TypeScript base config
├── tsconfig.node.json            # TypeScript config cho Node.js
├── vite.config.ts                # Vite configuration
├── public/                       # Static assets
│   └── vite.svg
└── src/
    ├── api.ts                    # Centralized API client
    ├── App.css                   # Global styles
    ├── App.tsx                   # Main app component với routing
    ├── index.css                 # Tailwind CSS imports
    ├── main.tsx                  # App entry point
    ├── assets/                   # Dynamic assets
    ├── components/               # Reusable UI components
    │   ├── ErrorBanner.tsx       # Global error display
    │   ├── Header.tsx            # Navigation header
    │   ├── Layout.tsx            # Main layout wrapper
    │   ├── RunSummary.tsx        # Run summary card
    │   ├── Statistics.tsx        # Analytics charts
    │   └── TickerSelector.tsx    # Ticker dropdown
    └── pages/                    # Page components
        ├── Analytics.tsx         # Analytics dashboard
        ├── PredictionTable.tsx   # Predictions table
        ├── RecentRuns.tsx        # Run selector
        └── TickerDetail.tsx      # Ticker detail page
```

### 5.3. Điểm Vào Chính

- **`src/main.tsx`**: Mount React app với BrowserRouter
- **`src/App.tsx`**: Define routes và global state (selectedRunId, globalError)
- **`src/api.ts`**: Centralized API calls với error handling

### 5.4. Luồng Dữ Liệu Frontend

```
User Interaction → Component State → API Call → Backend → Response → UI Update
```

- **State Management**: React useState hooks trong components
- **API Communication**: Fetch API với custom error handling
- **Error Handling**: Global ErrorBanner + component-level error states
- **Loading States**: Loading spinners cho tất cả async operations

## 6. Tính Năng Frontend

### 6.1. Điều Hướng và Layout

- **Header Navigation**: Dashboard / Analytics tabs
- **Utility Buttons**: Refresh, Copy Run ID, API Health Check, Open API Docs
- **Responsive Layout**: Grid system với Tailwind CSS
- **Breadcrumb Navigation**: Back buttons trong ticker detail

### 6.2. Trang Dashboard

**Bảng Dự Đoán:**
- Hiển thị: Ticker, Last Close, Pred Close, Delta, Pred Return (%), Confidence, Created At
- Filtering: Text search theo ticker
- Sorting: Click column headers
- Linking: Ticker links đến detail page

**Tóm Tắt Run:**
- Run ID, số lượng ticker, avg pred return, last updated
- Top 3 positive/negative predictions

**Chọn Run Gần Nhất:**
- List recent runs với metadata
- Click để switch run context

### 6.3. Trang Analytics

**KPI Cards:**
- Win Rate: % positive predictions
- Avg Confidence: Mean graph gate value
- Max/Min Return: Best/worst predictions

**Biểu Đồ:**
- Return Distribution: Histogram của pred_return
- Confidence Distribution: Histogram của graph_gate
- Confidence Breakdown: Pie chart (High/Medium/Low)
- Confidence vs Return: Scatter plot

**Bảng Tóm Tắt:**
- Top confident tickers
- Best/worst return predictions

### 6.4. Trang Chi Tiết Ticker

**Biểu Đồ Lịch Sử:**
- Price History: Line chart giá đóng cửa
- Prediction History: Bar chart pred_return
- Confidence Timeline: Line chart graph_gate

**Thẻ Tóm Tắt:**
- Current price, price change, latest confidence, pred return

**Export Feature:**
- Placeholder cho PDF/PNG export

### 6.5. Tính Năng Tiên Tiến

**Error Handling & Resilience:**
- Global error banner với dismiss
- APIError class cho structured errors
- Graceful degradation khi API fail
- Empty states với helpful messages

**User Experience:**
- Loading states cho tất cả operations
- Confidence badges (High/Medium/Low)
- Auto-dismiss notifications
- Responsive design

**Developer Experience:**
- Full TypeScript với strict mode
- Centralized API client
- Consistent error patterns
- Build verification (npm run build passes)

## 7. Các Endpoint Dữ Liệu

Frontend kết nối với backend API tại `http://localhost:8008`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | API health check |
| `/tickers` | GET | List available tickers |
| `/dashboard/summary` | GET | Dashboard summary stats |
| `/predictions/runs/recent` | GET | Recent prediction runs |
| `/predictions/runs/{run_id}` | GET | Predictions for specific run |
| `/predictions/runs/latest` | GET | Latest predictions |
| `/prices/ticker/{ticker}/history` | GET | Price history for ticker |
| `/predictions/ticker/{ticker}/history` | GET | Prediction history for ticker |
| `/docs` | GET | Swagger API documentation |

## 8. Build và Deployment

### 8.1. Development Build
```bash
cd frontend
npm run dev  # HMR enabled, port 5173
```

### 8.2. Production Build
```bash
cd frontend
npm run build  # Output to dist/
npm run preview  # Preview production build
```

### 8.3. Docker Deployment
```bash
# Build tất cả services
docker compose --env-file compose/.env -f compose/compose.yaml build

# Deploy production stack
docker compose --env-file compose/.env -f compose/compose.yaml --profile production up -d
```

## 9. Troubleshooting

### 9.1. Frontend Issues

**Không kết nối được backend:**
- Kiểm tra backend running: `curl http://localhost:8008/health`
- Verify CORS trong FastAPI config
- Check environment variables

**Build fails:**
- Clear node_modules: `rm -rf node_modules && npm install`
- Check TypeScript errors: `npm run build`
- Update dependencies: `npm update`

**Charts không render:**
- Check Recharts version compatibility
- Verify data format từ API
- Console errors trong browser dev tools

### 9.2. Backend Issues

**Services không start:**
- Check Docker Desktop running
- Verify .env file configuration
- Check disk space: `docker system df`

**Out of memory:**
- Increase Docker Desktop RAM allocation
- Reduce Spark batch sizes
- Monitor với `docker stats`

**Database connection fails:**
- Verify PostgreSQL credentials trong .env
- Check network connectivity giữa containers

## 10. Monitoring và Logs

### 10.1. Xem Logs Services
```bash
# API logs
docker compose logs api

# Inference logs
docker compose logs inference

# Airflow logs
docker compose logs airflow-webserver

# Frontend dev server logs (terminal window)
```

### 10.2. Health Monitoring
- **Frontend**: Error banner hiển thị API issues
- **Backend**: `/health` endpoint returns service status
- **Database**: Connection checks trong API logs
- **Inference**: Model loading status trong logs

### 10.3. Performance Monitoring
- Bundle size: `npm run build` output
- API response times: Browser network tab
- Memory usage: `docker stats`
- Error rates: Console logs

## 11. Ghi Chú Kỹ Thuật

### 11.1. Performance Optimizations
- Code splitting với React.lazy() (recommended for production)
- Bundle size: 663KB minified (194KB gzipped)
- Tree shaking enabled qua Vite
- Image optimization với Vite plugins

### 11.2. Security Considerations
- API calls sử dụng HTTPS trong production
- CORS configured properly
- Input validation trên backend
- No sensitive data exposed trong frontend

### 11.3. Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES2020+ features via Vite transpilation
- CSS Grid/Flexbox support required

### 11.4. Future Enhancements
- Dark mode toggle
- Real-time updates với WebSocket
- Chart export (PDF/PNG)
- Advanced filtering và search
- User authentication (nếu cần)
- PWA capabilities

## 12. Kết Luận

Frontend dashboard IE212 đã được triển khai hoàn chỉnh với:

- **Tính năng đầy đủ**: Dashboard, Analytics, Ticker Detail
- **UX/UI tốt**: Responsive, error handling, loading states
- **Code quality**: TypeScript, modern React patterns
- **Maintainability**: Modular architecture, centralized API
- **Performance**: Fast build, optimized bundle
- **Reliability**: Comprehensive error handling

Dự án sẵn sàng cho production deployment với Docker và có thể mở rộng dễ dàng cho các tính năng mới.
