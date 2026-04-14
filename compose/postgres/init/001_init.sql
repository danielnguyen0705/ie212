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