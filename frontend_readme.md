# IE212 Stock Prediction Dashboard

## 1. System Architecture

Project implements an end-to-end Big Data + Machine Learning pipeline for stock price prediction.

Pipeline flow:

Raw stock data
→ Feature engineering
→ Hybrid LSTM-GNN model inference
→ Batch prediction storage (PostgreSQL)
→ FastAPI serving layer
→ React dashboard visualization

System components:

* PostgreSQL: store prediction results
* FastAPI: backend API service
* Spark: data processing
* Airflow: pipeline orchestration
* Kafka: streaming layer (optional)
* MinIO: object storage
* React + Vite + TypeScript: frontend dashboard

---

# 2. Requirements

Before running the project, install:

## Required software

* Docker Desktop
* Node.js >= 18
* npm >= 9
* Git

Check versions:

```bash
docker --version
node -v
npm -v
git --version
```

---

# 3. Clone Repository

```bash
git clone https://github.com/<your-repo>.git
cd ie212
git checkout congan
```

---

# 4. Setup Environment Variables

Create `.env` file for Docker Compose:

Windows PowerShell:

```bash
Copy-Item compose\.env.example compose\.env
```

Linux / Mac:

```bash
cp compose/.env.example compose/.env
```

---

# 5. Start Backend System (Docker)

Run:

```bash
docker compose up -d --build
```

Wait until all containers start successfully.

Check running containers:

```bash
docker ps
```

Expected services:

* postgres
* kafka
* spark-master
* spark-worker
* airflow
* fastapi
* minio

---

# 6. Verify Backend Services

Open in browser:

Airflow:

```
http://localhost:8088
```

Spark master:

```
http://localhost:8080
```

MinIO:

```
http://localhost:9001
```

FastAPI docs:

```
http://localhost:8008/docs
```

Dashboard API summary:

```
http://localhost:8008/dashboard/summary
```

---

# 7. Run Frontend Dashboard

Move into frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

Open browser:

```
http://localhost:5173
```

---

# 8. Dashboard Features

Main dashboard:

* Prediction table
* Run summary
* Recent runs selector
* Filter ticker
* Copy run_id
* API health check
* Swagger docs shortcut

Ticker detail page:

* Actual vs predicted price chart
* Price history table
* Prediction history table

---

# 9. Useful API Endpoints

Latest run:

```
/predictions/runs/latest
```

Run detail:

```
/predictions/runs/{run_id}
```

Ticker price history:

```
/prices/ticker/{ticker}/history
```

Ticker prediction history:

```
/predictions/ticker/{ticker}/history
```

Dashboard summary:

```
/dashboard/summary
```

Swagger documentation:

```
/docs
```

---

# 10. Stop System

Stop all containers:

```bash
docker compose down
```

---

# 11. Restart System Later

If containers already built:

```bash
docker compose up -d
```

Run frontend again:

```bash
cd frontend
npm run dev
```

---

# 12. Project Structure

```
ie212/
│
├── compose/
├── services/
├── airflow/
├── frontend/
│   ├── components/
│   ├── pages/
│   └── App.tsx
│
└── README.md
```

---

# 13. Authors

IE212 Big Data Project

Frontend dashboard implemented with React + TypeScript + TailwindCSS.
