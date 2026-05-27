import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Zap,
} from "lucide-react";
import { getRunDetail, APIError, type PredictionItem } from "../api";
import ErrorBanner from "./ErrorBanner";

type StatisticsProps = {
  runId: string;
};

export default function Statistics({ runId }: StatisticsProps) {
  const [predictions, setPredictions] = useState<PredictionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getRunDetail(runId)
      .then((json) => {
        setPredictions(json.items ?? []);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof APIError) {
          setError(
            err.status === 404
              ? `Run not found: ${runId}`
              : err.detail || "Failed to load statistics"
          );
        } else {
          setError(err instanceof Error ? err.message : "Failed to load statistics");
        }
        setLoading(false);
      });
  }, [runId]);

  if (error) {
    return (
      <>
        <ErrorBanner error={error} onClose={() => setError(null)} />
        <div className="bg-white shadow rounded-xl p-6 text-center py-12">
          <p className="text-red-600 font-medium">{error}</p>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <div className="bg-white shadow rounded-xl p-6">
        <div className="text-center py-8 text-gray-500">
          Loading statistics...
        </div>
      </div>
    );
  }

  if (predictions.length === 0) {
    return (
      <div className="bg-white shadow rounded-xl p-6 text-center py-12">
        <p className="text-gray-400">No predictions available to analyze</p>
      </div>
    );
  }

  // ===== CALCULATIONS =====

  // Win rate
  const winCount = predictions.filter((p) => (p.pred_return ?? 0) >= 0).length;
  const winRate = predictions.length > 0 ? (winCount / predictions.length) * 100 : 0;

  // Avg confidence
  const avgConfidence =
    predictions.length > 0
      ? predictions.reduce((sum, p) => sum + (p.graph_gate ?? 0), 0) /
        predictions.length
      : 0;

  // Max/Min returns
  const returnValues = predictions.map((p) => p.pred_return ?? 0);
  const maxReturn = Math.max(...returnValues, 0);
  const minReturn = Math.min(...returnValues, 0);

  // Top/Bottom tickers by confidence
  const sortedByConfidence = [...predictions].sort(
    (a, b) => (b.graph_gate ?? 0) - (a.graph_gate ?? 0)
  );
  const topConfidentTickers = sortedByConfidence.slice(0, 5).map((p) => ({
    ticker: p.ticker,
    confidence: p.graph_gate ?? 0,
  }));

  // Top/Bottom tickers by return
  const sortedByReturn = [...predictions].sort(
    (a, b) => (b.pred_return ?? 0) - (a.pred_return ?? 0)
  );
  const topReturnTickers = sortedByReturn.slice(0, 5).map((p) => ({
    ticker: p.ticker,
    return: (p.pred_return ?? 0) * 100,
  }));
  const bottomReturnTickers = sortedByReturn.slice(-5).map((p) => ({
    ticker: p.ticker,
    return: (p.pred_return ?? 0) * 100,
  }));

  // Return distribution (bins)
  const returnBins = createBins(
    predictions.map((p) => (p.pred_return ?? 0) * 100),
    5
  );

  // Confidence distribution (bins)
  const confidenceBins = createBins(
    predictions.map((p) => p.graph_gate ?? 0),
    5
  );

  // Scatter data: confidence vs absolute return
  const scatterData = predictions.map((p) => ({
    x: p.graph_gate ?? 0,
    y: Math.abs(p.pred_return ?? 0) * 100,
    ticker: p.ticker,
  }));

  // Confidence brackets
  const highConfident = predictions.filter((p) => (p.graph_gate ?? 0) > 0.6).length;
  const mediumConfident = predictions.filter(
    (p) => (p.graph_gate ?? 0) >= 0.3 && (p.graph_gate ?? 0) <= 0.6
  ).length;
  const lowConfident = predictions.filter((p) => (p.graph_gate ?? 0) < 0.3).length;

  const confidenceBreakdown = [
    { name: "High (>0.6)", value: highConfident, fill: "#10b981" },
    { name: "Medium (0.3-0.6)", value: mediumConfident, fill: "#f59e0b" },
    { name: "Low (<0.3)", value: lowConfident, fill: "#ef4444" },
  ];


  return (
    <div className="space-y-6">
      {/* ===== KPI CARDS ===== */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Win Rate */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-5 shadow-sm border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 font-medium">Win Rate</p>
              <p className="text-3xl font-bold text-blue-900">
                {winRate.toFixed(1)}%
              </p>
              <p className="text-xs text-blue-600 mt-1">
                {winCount} / {predictions.length} positive
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-blue-300" />
          </div>
        </div>

        {/* Avg Confidence */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-5 shadow-sm border border-purple-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-600 font-medium">Avg Confidence</p>
              <p className="text-3xl font-bold text-purple-900">
                {(avgConfidence * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-purple-600 mt-1">
                Graph Gate Average
              </p>
            </div>
            <Zap className="w-12 h-12 text-purple-300" />
          </div>
        </div>

        {/* Max Return */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-5 shadow-sm border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-600 font-medium">Max Return</p>
              <p className="text-3xl font-bold text-green-900">
                {(maxReturn * 100).toFixed(2)}%
              </p>
              <p className="text-xs text-green-600 mt-1">
                Best prediction
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-green-300" />
          </div>
        </div>

        {/* Min Return */}
        <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-5 shadow-sm border border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-red-600 font-medium">Min Return</p>
              <p className="text-3xl font-bold text-red-900">
                {(minReturn * 100).toFixed(2)}%
              </p>
              <p className="text-xs text-red-600 mt-1">
                Worst prediction
              </p>
            </div>
            <TrendingDown className="w-12 h-12 text-red-300" />
          </div>
        </div>
      </div>

      {/* ===== CHARTS GRID ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Return Distribution */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-600" />
            Predicted Return Distribution
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={returnBins}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bin" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 2. Confidence Distribution */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-600" />
            Confidence (Graph Gate) Distribution
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={confidenceBins}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="bin" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#a855f7" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 3. Confidence Levels Pie */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-orange-600" />
            Confidence Breakdown
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={confidenceBreakdown}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={false}
                outerRadius={90}
                fill="#8884d8"
                dataKey="value"
              >
                {confidenceBreakdown.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-1 gap-2 text-sm text-gray-700">
            {confidenceBreakdown.map((entry) => (
              <div key={entry.name} className="flex items-center gap-3">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ backgroundColor: entry.fill }}
                />
                <span>{entry.name}</span>
                <span className="ml-auto font-semibold">{entry.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 4. Confidence vs Absolute Return Scatter */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-600" />
            Confidence vs Return Magnitude
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                name="Confidence"
                domain={[0, 1]}
                ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
                label={{ value: "Confidence (0-1)", position: "insideBottom", offset: -10 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Abs Return %"
                domain={[0, "dataMax"]}
                tickCount={5}
                tickFormatter={(value) =>
                  Number(value) === 0 ? "0" : Number(value).toFixed(4)
                }
                label={{
                  value: "Abs Return (%)",
                  angle: -90,
                  position: "left",
                  offset: 20,
                  dx: -20,
                  style: { textAnchor: "middle" },
                }}
              />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Scatter
                name="Predictions"
                data={scatterData}
                fill="#8b5cf6"
                fillOpacity={0.6}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ===== TOP/BOTTOM TICKERS ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Confident Tickers */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4">Top Confident Tickers</h3>
          <div className="space-y-3">
            {topConfidentTickers.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-purple-50 rounded-lg border border-purple-100">
                <div>
                  <p className="font-semibold text-gray-800">{item.ticker}</p>
                  <p className="text-xs text-gray-500">Confidence</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-purple-600">
                    {(item.confidence * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Return Tickers */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 text-green-600">Top Bullish Predictions</h3>
          <div className="space-y-3">
            {topReturnTickers.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-green-50 rounded-lg border border-green-100">
                <div>
                  <p className="font-semibold text-gray-800">{item.ticker}</p>
                  <p className="text-xs text-gray-500">Predicted Return</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-green-600">
                    +{item.return.toFixed(2)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Return Tickers */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 text-red-600">Top Bearish Predictions</h3>
          <div className="space-y-3">
            {bottomReturnTickers.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-red-50 rounded-lg border border-red-100">
                <div>
                  <p className="font-semibold text-gray-800">{item.ticker}</p>
                  <p className="text-xs text-gray-500">Predicted Return</p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-red-600">
                    {item.return.toFixed(2)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper: Create bins for distribution
function createBins(values: number[], numBins: number) {
  if (values.length === 0) return [];

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const niceStep = (value: number) => {
    const exponent = Math.floor(Math.log10(value));
    const fraction = value / Math.pow(10, exponent);
    let niceFraction;

    if (fraction <= 1) niceFraction = 1;
    else if (fraction <= 2) niceFraction = 2;
    else if (fraction <= 5) niceFraction = 5;
    else niceFraction = 10;

    return niceFraction * Math.pow(10, exponent);
  };

  const step = niceStep(range / numBins);
  const niceMin = Math.floor(min / step) * step;
  const decimals = Math.max(1, -Math.floor(Math.log10(step)));

  const formatLabel = (value: number) => {
    const normalized = Math.abs(value) < Math.pow(10, -decimals - 1) ? 0 : value;
    return normalized
      .toFixed(decimals)
      .replace(/^-0+(\.0+)?$/, "0.0");
  };

  const bins: { bin: string; count: number }[] = [];
  let start = niceMin;

  for (let i = 0; i < numBins; i++) {
    const end = start + step;
    const count = values.filter((v) =>
      i === numBins - 1 ? v >= start && v <= end : v >= start && v < end
    ).length;

    bins.push({
      bin: `${formatLabel(start)}-${formatLabel(end)}`,
      count,
    });
    start = end;
  }

  return bins;
}
