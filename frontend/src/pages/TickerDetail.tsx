import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Download, TrendingUp, TrendingDown, Target, Zap } from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { getPriceHistory, getPredictionHistory, APIError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

type PriceRow = {
  date: string;
  close: number;
};

type PredictionRow = {
  run_id: string;
  as_of_date?: string;
  pred_close: number;
  pred_return: number | null;
  graph_gate?: number | null;
  model_name?: string;
  created_at: string;
};

export default function TickerDetail() {
  const { ticker } = useParams();

  const [priceHistory, setPriceHistory] = useState<PriceRow[]>([]);
  const [predictionHistory, setPredictionHistory] = useState<PredictionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    Promise.all([
      getPriceHistory(ticker || "", 30)
        .then((data) => setPriceHistory(data.items ?? []))
        .catch((err) => {
          if (err instanceof APIError && err.status === 404) {
            throw new Error(`No price history found for ticker: ${ticker}`);
          }
          throw err;
        }),
      getPredictionHistory(ticker || "", 50)
        .then((data) => setPredictionHistory(data.items ?? []))
        .catch((err) => {
          if (err instanceof APIError && err.status === 404) {
            throw new Error(`No prediction history found for ticker: ${ticker}`);
          }
          throw err;
        }),
    ]).catch((err) => {
      if (err instanceof APIError) {
        setError(err.detail || "Failed to load data");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load ticker data");
      }
    }).finally(() => {
      setLoading(false);
    });
  }, [ticker]);

  if (error) {
    return (
      <>
        <ErrorBanner error={error} onClose={() => setError(null)} />
        <div className="min-h-screen bg-slate-50 p-6">
          <Link
            to="/"
            className="inline-block px-5 py-2 bg-green-400 text-white rounded-lg shadow-sm hover:bg-green-500 transition font-medium mb-4"
          >
            ← Back to Dashboard
          </Link>
          <div className="bg-white shadow rounded-xl p-6 text-center py-12">
            <p className="text-red-600 font-medium">{error}</p>
          </div>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="text-center text-gray-500">Loading...</div>
      </div>
    );
  }

  if (priceHistory.length === 0 && predictionHistory.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <Link
          to="/"
          className="inline-block px-5 py-2 bg-green-400 text-white rounded-lg shadow-sm hover:bg-green-500 transition font-medium mb-4"
        >
          ← Back to Dashboard
        </Link>
        <div className="bg-white shadow rounded-xl p-6 text-center py-12">
          <p className="text-gray-400">No data available for ticker {ticker}</p>
        </div>
      </div>
    );
  }

  // ===== CALCULATIONS =====

  const currentPrice = priceHistory.length > 0 ? priceHistory[priceHistory.length - 1].close : 0;
  const prevPrice = priceHistory.length > 1 ? priceHistory[priceHistory.length - 2].close : currentPrice;
  const priceChange = currentPrice - prevPrice;
  const priceChangePercent = prevPrice > 0 ? (priceChange / prevPrice) * 100 : 0;

  const latestPrediction = predictionHistory.length > 0 ? predictionHistory[0] : null;
  const latestConfidence = latestPrediction?.graph_gate ?? 0;
  const predictedChange = latestPrediction?.pred_return ?? 0;

  const minPrice = Math.min(...priceHistory.map((p) => p.close));
  const maxPrice = Math.max(...priceHistory.map((p) => p.close));
  const avgPrice = priceHistory.length > 0 
    ? priceHistory.reduce((sum, p) => sum + p.close, 0) / priceHistory.length 
    : 0;

  const latestPred = latestPrediction?.pred_close ?? null;
  const mergedChartData = priceHistory.map((p) => ({
    date: p.date,
    close: p.close,
    pred_close: latestPred,
  }));

  // Prediction trend: reverse so oldest is first
  const predictionTrendData = [...predictionHistory]
    .reverse()
    .map((p) => ({
      date: p.created_at ? new Date(p.created_at).toLocaleDateString() : p.run_id.slice(-8),
      pred_close: p.pred_close,
      actual: currentPrice,
    }));

  // Confidence timeline
  const confidenceTimelineData = [...predictionHistory]
    .reverse()
    .map((p) => ({
      date: p.created_at ? new Date(p.created_at).toLocaleDateString() : p.run_id.slice(-8),
      confidence: (p.graph_gate ?? 0) * 100,
    }));

  // Download chart as PNG (helper)
  const downloadChart = () => {
    alert("Export feature: In production, integrate html2canvas library");
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <Link
            to="/"
            className="inline-block px-5 py-2 bg-green-400 text-white rounded-lg shadow-sm hover:bg-green-500 transition font-medium mb-4"
          >
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold">
            {ticker} — Ticker Detail
          </h1>
        </div>
        <button
          onClick={downloadChart}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* ===== KPI CARDS ===== */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Current Price */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-5 shadow-sm border border-blue-200">
          <p className="text-sm text-blue-600 font-medium">Current Price</p>
          <p className="text-3xl font-bold text-blue-900 mt-2">
            ${currentPrice.toFixed(2)}
          </p>
          <p className="text-xs text-blue-600 mt-2">Latest close price</p>
        </div>

        {/* Price Change */}
        <div className={`rounded-xl p-5 shadow-sm border ${
          priceChange >= 0
            ? "bg-gradient-to-br from-green-50 to-green-100 border-green-200"
            : "bg-gradient-to-br from-red-50 to-red-100 border-red-200"
        }`}>
          <p className={`text-sm font-medium ${priceChange >= 0 ? "text-green-600" : "text-red-600"}`}>
            Price Change
          </p>
          <div className="flex items-center gap-2 mt-2">
            {priceChange >= 0 ? (
              <TrendingUp className="w-6 h-6 text-green-600" />
            ) : (
              <TrendingDown className="w-6 h-6 text-red-600" />
            )}
            <p className={`text-3xl font-bold ${priceChange >= 0 ? "text-green-900" : "text-red-900"}`}>
              {priceChangePercent.toFixed(2)}%
            </p>
          </div>
          <p className={`text-xs mt-2 ${priceChange >= 0 ? "text-green-600" : "text-red-600"}`}>
            {priceChange >= 0 ? "+" : ""}{priceChange.toFixed(2)}
          </p>
        </div>

        {/* Latest Confidence */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-5 shadow-sm border border-purple-200">
          <p className="text-sm text-purple-600 font-medium">Latest Confidence</p>
          <p className="text-3xl font-bold text-purple-900 mt-2">
            {(latestConfidence * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-purple-600 mt-2">
            {latestConfidence > 0.6
              ? "High"
              : latestConfidence >= 0.3
              ? "Medium"
              : "Low"}
          </p>
        </div>

        {/* Predicted Change */}
        <div className={`rounded-xl p-5 shadow-sm border ${
          predictedChange >= 0
            ? "bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-200"
            : "bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200"
        }`}>
          <p className={`text-sm font-medium ${predictedChange >= 0 ? "text-emerald-600" : "text-orange-600"}`}>
            Predicted Return
          </p>
          <p className={`text-3xl font-bold mt-2 ${predictedChange >= 0 ? "text-emerald-900" : "text-orange-900"}`}>
            {predictedChange >= 0 ? "+" : ""}{(predictedChange * 100).toFixed(2)}%
          </p>
          <p className={`text-xs mt-2 ${predictedChange >= 0 ? "text-emerald-600" : "text-orange-600"}`}>
            Next day target
          </p>
        </div>
      </div>

      {/* ===== MAIN CHARTS ===== */}
      <div className="space-y-6">
        {/* Actual vs Predicted Price */}
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-600" />
            Actual vs Predicted Price
          </h2>
          <div className="h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mergedChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="close"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={false}
                  name="Actual Price"
                />
                {latestPred && (
                  <Line
                    type="monotone"
                    dataKey="pred_close"
                    stroke="#e10f21"
                    strokeDasharray="5 5"
                    strokeWidth={2}
                    dot={false}
                    name="Predicted Price"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Prediction Trend */}
        {predictionTrendData.length > 0 && (
          <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-indigo-600" />
              Prediction Trend (Over Runs)
            </h2>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={predictionTrendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#059669"
                    strokeWidth={2}
                    dot={false}
                    name="Current Actual Price"
                  />
                  <Line
                    type="monotone"
                    dataKey="pred_close"
                    stroke="#7c3aed"
                    strokeWidth={2}
                    dot={false}
                    name="Predicted Price"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Shows how model predictions evolved across different runs
            </p>
          </div>
        )}

        {/* Confidence Timeline */}
        {confidenceTimelineData.length > 0 && (
          <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-purple-600" />
              Confidence Timeline
            </h2>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={confidenceTimelineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc' }}
                    labelFormatter={(label) => `${label}`}
                  />
                  <Bar dataKey="confidence" fill="#a855f7" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              How confident the model was in each prediction run
            </p>
          </div>
        )}
      </div>

      {/* ===== STATISTICS + TABLES ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Price Statistics */}
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">Price Statistics</h2>
          <div className="space-y-3">
            <StatRow label="Min Price" value={`$${minPrice.toFixed(2)}`} highlight="text-red-600" />
            <StatRow label="Max Price" value={`$${maxPrice.toFixed(2)}`} highlight="text-green-600" />
            <StatRow label="Avg Price" value={`$${avgPrice.toFixed(2)}`} highlight="text-blue-600" />
            <StatRow label="Current" value={`$${currentPrice.toFixed(2)}`} highlight="text-purple-600" />
            <div className="border-t pt-3 mt-3">
              <StatRow
                label="Range"
                value={`$${(maxPrice - minPrice).toFixed(2)}`}
                highlight="text-gray-600"
              />
              <StatRow
                label="Volatility"
                value={`${(((maxPrice - minPrice) / avgPrice) * 100).toFixed(2)}%`}
                highlight="text-orange-600"
              />
            </div>
          </div>
        </div>

        {/* Price History Table */}
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">Price History (Last 30 days)</h2>
          <div className="overflow-auto max-h-[420px]">
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-gray-500 border-b sticky top-0 bg-gray-50">
                <tr>
                  <th className="p-3 text-left">Date</th>
                  <th className="p-3 text-left">Close</th>
                </tr>
              </thead>
              <tbody>
                {priceHistory.map((row) => (
                  <tr key={row.date} className="border-b hover:bg-slate-50 transition">
                    <td className="p-3 text-gray-700">{row.date}</td>
                    <td className="p-3 font-medium text-gray-900">${row.close.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Prediction History Table */}
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">Prediction History</h2>
          <div className="overflow-auto max-h-[420px]">
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-gray-500 border-b sticky top-0 bg-gray-50">
                <tr>
                  <th className="p-3 text-left">Pred Close</th>
                  <th className="p-3 text-left">Return</th>
                  <th className="p-3 text-left">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {predictionHistory.map((row, idx) => (
                  <tr key={idx} className="border-b hover:bg-slate-50 transition">
                    <td className="p-3 font-medium text-gray-900">${row.pred_close.toFixed(2)}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          (row.pred_return ?? 0) >= 0
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {(row.pred_return ?? 0) >= 0 ? "+" : ""}{((row.pred_return ?? 0) * 100).toFixed(2)}%
                      </span>
                    </td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          (row.graph_gate ?? 0) > 0.6
                            ? "bg-green-100 text-green-700"
                            : (row.graph_gate ?? 0) >= 0.3
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {((row.graph_gate ?? 0) * 100).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: string;
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-600 text-sm">{label}</span>
      <span className={`font-semibold ${highlight || "text-gray-900"}`}>{value}</span>
    </div>
  );
}