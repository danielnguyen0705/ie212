import { useEffect, useState } from "react";
import { getStreamLatest, getAIAnalyze } from "../api";

interface StockRecommendation {
  ticker: string;
  runtime_price: number;
  last_close: number;
  pred_close: number;
  pred_return: number;
  delta: number;
  signal: string;
  graph_gate: number;
}

interface AIDrawerContent {
  signal: string;
  confidence: string;
  reasons: string;
  risks: string;
  supporting_factors: string[];
  risk_factors: string[];
  missing_data_warnings: string[];
}

export default function AIDecision() {
  const [data, setData] = useState<StockRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedStock, setSelectedStock] = useState<StockRecommendation | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIDrawerContent | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    let active = true;

    const fetchLatest = () => {
      getStreamLatest()
        .then((items) => {
          if (active) {
            setData(items ?? []);
            setLoading(false);
          }
        })
        .catch((err) => console.error("Error loading stock signals", err));
    };

    fetchLatest();
    const interval = setInterval(fetchLatest, 3000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const handleOpenDrawer = (stock: StockRecommendation) => {
    setSelectedStock(stock);
    setDrawerOpen(true);
    setAiLoading(true);
    setAiAnalysis(null);

    getAIAnalyze(stock.ticker, stock.runtime_price, stock.delta)
      .then((res) => {
        setAiAnalysis(res);
        setAiLoading(false);
      })
      .catch((err) => {
        console.error("AI analyze error:", err);
        setAiLoading(false);
      });
  };

  const getSignalTranslation = (sig: string) => {
    const s = String(sig).toUpperCase();
    if (s === "BUY") return { label: "MUA", color: "bg-green-100 text-green-800 border-green-200" };
    if (s === "SELL_OR_AVOID" || s === "SELL") return { label: "BÁN / TRÁNH", color: "bg-red-100 text-red-800 border-red-200" };
    return { label: "GIỮ", color: "bg-blue-100 text-blue-800 border-blue-200" };
  };

  if (loading) {
    return (
      <div className="bg-white shadow rounded-2xl p-6 text-center py-12">
        <div className="text-gray-500">Đang tải luồng tín hiệu khuyến nghị AI...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.map((stock) => {
          const sig = getSignalTranslation(stock.signal);
          return (
            <div
              key={stock.ticker}
              onClick={() => handleOpenDrawer(stock)}
              className="bg-white hover:bg-slate-50 border shadow-sm rounded-2xl p-5 flex justify-between items-center cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
            >
              <div>
                <div className="text-lg font-bold text-slate-800">{stock.ticker}</div>
                <div className="text-sm text-slate-500">
                  Giá: <span className="font-mono font-bold text-slate-700">${stock.runtime_price.toFixed(4)}</span>
                </div>
              </div>

              <span className={`px-4 py-1.5 rounded-full text-xs font-black border uppercase tracking-wider ${sig.color}`}>
                KHUYẾN NGHỊ: {sig.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* DRAWER PHÂN TÍCH CHI TIẾT AI */}
      <div
        className={`fixed top-0 right-0 h-full w-full max-w-lg bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out border-l flex flex-col ${
          drawerOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex justify-between items-center p-5 border-b bg-slate-50">
          <h2 className="text-xl font-bold text-slate-800">
            Phân tích cổ phiếu {selectedStock?.ticker}
          </h2>
          <button
            onClick={() => setDrawerOpen(false)}
            className="text-2xl font-semibold text-slate-400 hover:text-slate-600 outline-none"
          >
            &times;
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {aiLoading && (
            <div className="flex flex-col items-center justify-center py-12 space-y-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <div className="text-sm text-slate-500">Gemini AI đang lập luận phân tích...</div>
            </div>
          )}

          {aiAnalysis && selectedStock && (
            <div className="space-y-6">
              {/* Recommendation Pill */}
              <div className="text-center">
                <span className={`px-6 py-2.5 rounded-xl text-sm font-black border inline-block ${getSignalTranslation(aiAnalysis.signal).color}`}>
                  KHUYẾN NGHỊ: {getSignalTranslation(aiAnalysis.signal).label} <br />
                  <span className="text-[11px] font-bold">
                    (Độ tin cậy: {aiAnalysis.confidence === "high" || aiAnalysis.confidence === "CAO" ? "CAO" : "TRUNG BÌNH"})
                  </span>
                </span>
              </div>

              {/* Realtime stats card */}
              <div className="bg-slate-50 rounded-2xl p-4 border space-y-2.5">
                <h3 className="font-bold text-sm text-slate-800">Thông số thời gian thực</h3>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Giá hiện tại:</span>
                  <span className="font-mono font-bold text-slate-700">${selectedStock.runtime_price.toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Giá dự đoán tiếp theo:</span>
                  <span className="font-mono font-bold text-slate-700">${selectedStock.pred_close.toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Biến động (Delta):</span>
                  <span className={`font-mono font-bold ${selectedStock.delta >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {selectedStock.delta >= 0 ? "+" : ""}{selectedStock.delta.toFixed(6)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Tỷ suất dự đoán:</span>
                  <span className={`font-mono font-bold ${(selectedStock.pred_return ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                    {((selectedStock.pred_return ?? 0) * 100).toFixed(4)}%
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Trọng số cổng đồ thị GNN:</span>
                  <span className="font-mono font-bold text-slate-700">{(selectedStock.graph_gate ?? 0).toFixed(3)}</span>
                </div>
              </div>

              {/* Lập luận chi tiết */}
              <div className="space-y-4">
                <div className="bg-green-50 border border-green-150 rounded-2xl p-4 space-y-1.5">
                  <h4 className="font-bold text-sm text-green-700">Lý do khuyến nghị</h4>
                  <p className="text-xs text-green-900 leading-relaxed">{aiAnalysis.reasons}</p>
                </div>

                <div className="bg-red-50 border border-red-150 rounded-2xl p-4 space-y-1.5">
                  <h4 className="font-bold text-sm text-red-700">Cảnh báo rủi ro</h4>
                  <p className="text-xs text-red-900 leading-relaxed">{aiAnalysis.risks}</p>
                </div>
              </div>

              {/* Các yếu tố phụ trợ */}
              {aiAnalysis.supporting_factors && aiAnalysis.supporting_factors.length > 0 && (
                <div className="space-y-1">
                  <strong className="text-xs text-green-700">Yếu tố kỹ thuật bổ trợ:</strong>
                  <ul className="list-disc pl-5 text-[11px] text-slate-600 leading-relaxed space-y-1">
                    {aiAnalysis.supporting_factors.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {aiAnalysis.risk_factors && aiAnalysis.risk_factors.length > 0 && (
                <div className="space-y-1">
                  <strong className="text-xs text-red-700">Yếu tố nguy hiểm cảnh báo:</strong>
                  <ul className="list-disc pl-5 text-[11px] text-slate-600 leading-relaxed space-y-1">
                    {aiAnalysis.risk_factors.map((rf, i) => (
                      <li key={i}>{rf}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Background overlay when drawer open */}
      {drawerOpen && (
        <div
          onClick={() => setDrawerOpen(false)}
          className="fixed inset-0 bg-slate-900 bg-opacity-40 z-40 transition-opacity duration-300"
        ></div>
      )}
    </div>
  );
}
