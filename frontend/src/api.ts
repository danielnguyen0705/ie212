// Shared API client with error handling

const API_BASE = "http://localhost:8008";

export class APIError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, detail?: string, message?: string) {
    super(message || detail || `API Error: ${status}`);
    this.name = "APIError";
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  // Check if response is ok
  if (!res.ok) {
    let detail = "";
    try {
      const json = await res.json();
      detail = json.detail || `HTTP ${res.status}`;
    } catch {
      detail = `HTTP ${res.status}`;
    }
    throw new APIError(res.status, detail);
  }

  try {
    return await res.json();
  } catch (e) {
    throw new Error("Failed to parse JSON response");
  }
}

// ===== API Endpoints =====

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return handleResponse<{
    status: string;
    database: boolean;
    inference_predictions_table: boolean;
  }>(res);
}

export async function getTickers() {
  const res = await fetch(`${API_BASE}/tickers`);
  return handleResponse<{ tickers: string[] }>(res);
}

export async function getDashboardSummary() {
  const res = await fetch(`${API_BASE}/dashboard/summary`);
  return handleResponse<{
    latest_run_id: string;
    model_name: string;
    as_of_date: string | null;
    row_count: number;
    ticker_count: number;
    avg_pred_return: number;
    max_pred_return: number;
    min_pred_return: number;
    last_updated: string;
  }>(res);
}

export interface PredictionItem {
  ticker: string;
  last_close: number;
  pred_close: number;
  pred_return: number | null;
  graph_gate: number | null;
  created_at: string | null;
}

export interface RunResponse {
  run_id: string;
  as_of_date: string | null;
  model_name: string;
  row_count: number;
  items: PredictionItem[];
}

export async function getLatestPredictions() {
  const res = await fetch(`${API_BASE}/predictions/runs/latest`);
  return handleResponse<RunResponse>(res);
}

export async function getRecentRuns(limit: number = 10) {
  const res = await fetch(`${API_BASE}/predictions/runs/recent?limit=${limit}`);
  return handleResponse<{
    count: number;
    items: Array<{
      run_id: string;
      as_of_date: string | null;
      model_name: string;
      row_count: number;
      first_created_at: string;
      last_created_at: string;
    }>;
  }>(res);
}

export async function getRunDetail(runId: string) {
  const res = await fetch(`${API_BASE}/predictions/runs/${runId}`);
  return handleResponse<RunResponse>(res);
}

export async function getPredictionHistory(ticker: string, limit: number = 30) {
  const res = await fetch(
    `${API_BASE}/predictions/ticker/${ticker}/history?limit=${limit}`
  );
  return handleResponse<{
    ticker: string;
    items: Array<{
      run_id: string;
      as_of_date?: string;
      last_close: number;
      pred_close: number;
      pred_return: number | null;
      graph_gate: number | null;
      model_name?: string;
      created_at: string;
    }>;
  }>(res);
}

export async function getPriceHistory(ticker: string, days: number = 30) {
  const res = await fetch(
    `${API_BASE}/prices/ticker/${ticker}/history?days=${days}`
  );
  return handleResponse<{
    ticker: string;
    days: number;
    items: Array<{
      date: string;
      close: number;
    }>;
  }>(res);
}
