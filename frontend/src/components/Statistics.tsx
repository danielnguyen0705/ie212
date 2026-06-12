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
    let active = true;

    const fetchStats = () => {
      getRunDetail(runId)
        .then((json) => {
          if (active) {
            setPredictions(json.items ?? []);
            setLoading(false);
          }
        })
        .catch((err) => {
          if (active) {
            if (err instanceof APIError) {
              setError(
                err.status === 404
                  ? `Không tìm thấy phiên dự báo: ${runId}`
                  : err.detail || "Không thể tải số liệu thống kê"
              );
            } else {
              setError(err instanceof Error ? err.message : "Không thể tải số liệu thống kê");
            }
            setLoading(false);
          }
        });
    };

    setLoading(true);
    setError(null);
    fetchStats();

    // Polling mỗi 3 giây để cập nhật số liệu thời gian thực
    const interval = setInterval(fetchStats, 3000);

    return () => {
      active = false;
      clearInterval(interval);
    };
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
          Đang tải dữ liệu phân tích thống kê...
        </div>
      </div>
    );
  }

  if (predictions.length === 0) {
    return (
      <div className="bg-white shadow rounded-xl p-6 text-center py-12">
        <p className="text-gray-400">Không có dữ liệu dự đoán để phân tích</p>
      </div>
    );
  }

  // ===== TÍNH TOÁN CÁC CHỈ SỐ =====

  // Tỷ lệ dự đoán tăng (Win Rate giả lập)
  const winCount = predictions.filter((p) => (p.pred_return ?? 0) >= 0).length;
  const winRate = predictions.length > 0 ? (winCount / predictions.length) * 100 : 0;

  // Độ tin cậy trung bình của GCN
  const avgConfidence =
    predictions.length > 0
      ? predictions.reduce((sum, p) => sum + (p.graph_gate ?? 0), 0) /
        predictions.length
      : 0;

  // Lợi nhuận lớn nhất/nhỏ nhất dự đoán
  const returnValues = predictions.map((p) => p.pred_return ?? 0);
  const maxReturn = Math.max(...returnValues, 0);
  const minReturn = Math.min(...returnValues, 0);

  // Top cổ phiếu có độ tin cậy cao nhất
  const sortedByConfidence = [...predictions].sort(
    (a, b) => (b.graph_gate ?? 0) - (a.graph_gate ?? 0)
  );
  const topConfidentTickers = sortedByConfidence.slice(0, 5).map((p) => ({
    ticker: p.ticker,
    confidence: p.graph_gate ?? 0,
  }));

  // Top cổ phiếu tăng/giảm mạnh nhất
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

  // Phân phối tỷ suất lợi nhuận (bins)
  const returnBins = createBins(
    predictions.map((p) => (p.pred_return ?? 0) * 100),
    5
  );

  // Phân phối độ tin cậy (bins)
  const confidenceBins = createBins(
    predictions.map((p) => p.graph_gate ?? 0),
    5
  );

  // Biểu đồ phân tán: độ tin cậy vs biến động tuyệt đối
  const scatterData = predictions.map((p) => ({
    x: p.graph_gate ?? 0,
    y: Math.abs(p.pred_return ?? 0) * 100,
    ticker: p.ticker,
  }));

  // Phân loại độ tin cậy
  const highConfident = predictions.filter((p) => (p.graph_gate ?? 0) > 0.6).length;
  const mediumConfident = predictions.filter(
    (p) => (p.graph_gate ?? 0) >= 0.3 && (p.graph_gate ?? 0) <= 0.6
  ).length;
  const lowConfident = predictions.filter((p) => (p.graph_gate ?? 0) < 0.3).length;

  const confidenceBreakdown = [
    { name: "Cao (>0.6)", value: highConfident, fill: "#10b981" },
    { name: "Trung bình (0.3-0.6)", value: mediumConfident, fill: "#f59e0b" },
    { name: "Thấp (<0.3)", value: lowConfident, fill: "#ef4444" },
  ];

  return (
    <div className="space-y-6">
      {/* ===== THẺ KPI ===== */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Win Rate */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-5 shadow-sm border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-600 font-medium">Tỷ Lệ Tăng Dự Đoán</p>
              <p className="text-3xl font-bold text-blue-900">
                {winRate.toFixed(1)}%
              </p>
              <p className="text-xs text-blue-600 mt-1">
                {winCount} / {predictions.length} mã dự kiến tăng
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-blue-300" />
          </div>
        </div>

        {/* Avg Confidence */}
        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl p-5 shadow-sm border border-purple-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-purple-600 font-medium">Độ Tin Cậy Trung Bình</p>
              <p className="text-3xl font-bold text-purple-900">
                {(avgConfidence * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-purple-600 mt-1">
                Hệ số Graph Gate bình quân
              </p>
            </div>
            <Zap className="w-12 h-12 text-purple-300" />
          </div>
        </div>

        {/* Max Return */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-5 shadow-sm border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-600 font-medium">Tăng Lớn Nhất Kỳ Vọng</p>
              <p className="text-3xl font-bold text-green-900">
                {(maxReturn * 100).toFixed(2)}%
              </p>
              <p className="text-xs text-green-600 mt-1">
                Khuyến nghị tăng cao nhất
              </p>
            </div>
            <TrendingUp className="w-12 h-12 text-green-300" />
          </div>
        </div>

        {/* Min Return */}
        <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-5 shadow-sm border border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-red-600 font-medium">Giảm Nhiều Nhất Kỳ Vọng</p>
              <p className="text-3xl font-bold text-red-900">
                {(minReturn * 100).toFixed(2)}%
              </p>
              <p className="text-xs text-red-600 mt-1">
                Khuyến nghị giảm sâu nhất
              </p>
            </div>
            <TrendingDown className="w-12 h-12 text-red-300" />
          </div>
        </div>
      </div>

      {/* ===== BIỂU ĐỒ ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Return Distribution */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-1 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-600" />
            Phân phối Tỷ suất sinh lời dự kiến (%)
          </h3>
          <p className="text-xs text-slate-400 mb-4 leading-relaxed">
            Biểu đồ cột này thể hiện sự phân bổ kỳ vọng tăng giảm giá của các cổ phiếu. Cột lệch phải thể hiện thị trường đang tích cực; lệch trái thể hiện thị trường tiêu cực.
          </p>
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
          <h3 className="text-lg font-semibold mb-1 flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-600" />
            Phân bổ mức độ tin cậy GNN
          </h3>
          <p className="text-xs text-slate-400 mb-4 leading-relaxed">
            Biểu diễn tỷ lệ độ tin cậy của GCN. Mức <b>Cao</b> thể hiện mối quan hệ ngành của cổ phiếu đang có tác động mạnh mẽ; mức <b>Thấp</b> thể hiện mô hình chỉ đang dựa trên xu hướng chuỗi thời gian nội tại.
          </p>
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
            Phân bổ mức độ tin cậy GNN
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
            Độ tương quan: Độ tin cậy vs Biên độ biến động
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="x"
                name="Độ tin cậy"
                domain={[0, 1]}
                ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
                label={{ value: "Độ tin cậy (0-1)", position: "insideBottom", offset: -10 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Biến động tuyệt đối %"
                domain={[0, "dataMax"]}
                tickCount={5}
                tickFormatter={(value) =>
                  Number(value) === 0 ? "0" : Number(value).toFixed(4)
                }
                label={{
                  value: "Biến động (%)",
                  angle: -90,
                  position: "left",
                  offset: 20,
                  dx: -20,
                  style: { textAnchor: "middle" },
                }}
              />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Scatter
                name="Cổ phiếu"
                data={scatterData}
                fill="#8b5cf6"
                fillOpacity={0.6}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ===== BẢNG TOP CỔ PHIẾU ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Confident Tickers */}
        <div className="bg-white shadow rounded-xl p-6 border border-gray-100">
          <h3 className="text-lg font-semibold mb-4 text-slate-800">Top Tin Cậy Cao Nhất</h3>
          <div className="space-y-3">
            {topConfidentTickers.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-purple-50 rounded-lg border border-purple-100">
                <div>
                  <p className="font-semibold text-gray-800">{item.ticker}</p>
                  <p className="text-xs text-gray-500">Mức tin cậy</p>
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
          <h3 className="text-lg font-semibold mb-4 text-green-600">Top Cổ Phiếu Tăng Mạnh</h3>
          <div className="space-y-3">
            {topReturnTickers.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-green-50 rounded-lg border border-green-100">
                <div>
                  <p className="font-semibold text-gray-800">{item.ticker}</p>
                  <p className="text-xs text-gray-500">Tỷ suất kỳ vọng</p>
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
          <h3 className="text-lg font-semibold mb-4 text-red-600">Top Cổ Phiếu Giảm Mạnh</h3>
          <div className="space-y-3">
            {bottomReturnTickers.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-red-50 rounded-lg border border-red-100">
                <div>
                  <p className="font-semibold text-gray-800">{item.ticker}</p>
                  <p className="text-xs text-gray-500">Tỷ suất kỳ vọng</p>
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

// Helper: Phân nhóm bins dữ liệu
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
      bin: `${formatLabel(start)} đến ${formatLabel(end)}`,
      count,
    });
    start = end;
  }

  return bins;
}
