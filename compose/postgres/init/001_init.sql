CREATE SCHEMA IF NOT EXISTS stock;

CREATE TABLE IF NOT EXISTS stock.predictions (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    prediction_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    target_date DATE,
    predicted_close DOUBLE PRECISION,
    actual_close DOUBLE PRECISION,
    mse DOUBLE PRECISION,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS stock.model_registry (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    storage_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_predictions_symbol_time
    ON stock.predictions(symbol, prediction_time DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_model_registry_name_version
    ON stock.model_registry(model_name, model_version);

-- Cấu trúc bảng inference_predictions cho Dashboard thời gian thực
CREATE TABLE IF NOT EXISTS stock.inference_predictions (
    id BIGSERIAL PRIMARY KEY,
    prediction_run_id TEXT NOT NULL,
    as_of_date DATE,
    model_name TEXT NOT NULL,
    checkpoint_path TEXT,
    input_npz_path TEXT,
    output_json_path TEXT,
    device TEXT,
    ticker TEXT NOT NULL,
    last_close DOUBLE PRECISION NOT NULL,
    pred_close DOUBLE PRECISION NOT NULL,
    pred_return DOUBLE PRECISION,
    graph_gate DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (prediction_run_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_inference_predictions_created_at 
    ON stock.inference_predictions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_inference_predictions_ticker 
    ON stock.inference_predictions (ticker);

-- Chèn dữ liệu dự phòng ban đầu để Dashboard hoạt động tức thì khi dựng Postgres
INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'AAPL', 310.86, 310.8584, -0.000005, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'ADBE', 238.87, 238.8678, -0.000009, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'AMD', 498.71, 498.7088, -0.000002, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'CMCSA', 25.2385, 25.2393, 0.000031, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'COST', 382.11, 382.1098, -0.000001, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'INTC', 42.15, 42.1525, 0.000059, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'INTU', 255.42, 255.4242, 0.000016, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'MSFT', 412.56, 412.5684, 0.000020, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'QCOM', 165.84, 165.8398, -0.000001, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;

INSERT INTO stock.inference_predictions (
    prediction_run_id, as_of_date, model_name, ticker, last_close, pred_close, pred_return, graph_gate
) VALUES 
('kafka_inference_latest', '2026-05-28', 'hybrid_expanding_best_full-kafka', 'TXN', 170.22, 170.2198, -0.000001, 0.0)
ON CONFLICT (prediction_run_id, ticker) DO NOTHING;
