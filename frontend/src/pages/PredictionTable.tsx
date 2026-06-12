import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStreamLatest, APIError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

export interface StreamItem {
  ticker: string;
  runtime_price: number;
  last_close: number;
  pred_close: number;
  pred_return: number | null;
  delta: number;
  signal: string;
  graph_gate: number | null;
  timestamp: string;
}

export default function PredictionTable({
  runId,
}: {
  runId: string;
}) {
  const [data, setData] = useState<StreamItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let active = true;

    const fetchStreamData = () => {
      getStreamLatest()
        .then((items) => {
          if (active) {
            setData(items ?? []);
            setLoading(false);
          }
        })
        .catch((err) => {
          if (active) {
            if (err instanceof APIError) {
              setError(err.detail || "Không thể kết nối luồng dữ liệu thời gian thực");
            } else {
              setError(err instanceof Error ? err.message : "Không thể kết nối luồng dữ liệu");
            }
            setLoading(false);
          }
        });
    };

    setLoading(true);
    setError(null);
    fetchStreamData();

    // Polling liên tục mỗi 3 giây để cập nhật giá thời gian thực
    const interval = setInterval(fetchStreamData, 3000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [runId]);

  const filtered = data.filter((item) =>
    item.ticker.toLowerCase().includes(filter.toLowerCase())
  );

  if (error) {
    return (
      <>
        <ErrorBanner error={error} onClose={() => setError(null)} />
        <div className="bg-white shadow rounded-xl p-6 text-center py-12">
          <p className="text-red-600 font-medium">Lỗi kết nối: {error}</p>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <div className="bg-white shadow rounded-xl p-6">
        <div className="text-center py-8 text-gray-500">
          Đang tải dữ liệu thời gian thực...
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white shadow rounded-xl p-6 text-center py-12">
        <p className="text-gray-400">Không có dữ liệu thời gian thực.</p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-xl p-6">

      {/* HEADER */}
      <div className="flex justify-between items-center mb-4 border-b pb-3">
        <h2 className="text-xl font-bold text-slate-800">
          Bảng thống kê dự đoán giá
        </h2>
        <div id="rowsInfo" className="text-sm text-gray-500 font-medium bg-slate-100 px-3 py-1 rounded-full">
          Đang hiển thị {filtered.length} / {data.length} dòng
        </div>
      </div>

      {/* FILTER */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Tìm mã cổ phiếu..."
          className="border rounded-lg px-4 py-2 w-full max-w-xs focus:ring-2 focus:ring-blue-500 outline-none transition-all duration-200"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {/* TABLE */}
      <div className="overflow-auto max-h-[420px] rounded-lg border">
        {filtered.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            Không có cổ phiếu nào khớp với bộ lọc "{filter}"
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-gray-600 border-b bg-gray-50 font-semibold">
              <tr>
                <th className="p-3 text-left">Mã cổ phiếu</th>
                <th className="p-3 text-left">Giá Đóng Cửa Trước</th>
                <th className="p-3 text-left">Giá Thực Tế</th>
                <th className="p-3 text-left">Biến động (Delta)</th>
                <th className="p-3 text-left">Tỷ suất dự đoán (%)</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const deltaClass = item.delta > 0 ? "text-green-600 font-semibold" : item.delta < 0 ? "text-red-600 font-semibold" : "text-gray-600";
                
                return (
                  <tr
                    key={item.ticker}
                    className="border-b hover:bg-gray-50 transition-colors duration-150"
                  >
                    {/* TICKER */}
                    <td className="p-3 font-bold text-blue-600">
                      <Link
                        to={`/ticker/${item.ticker}`}
                        className="hover:underline"
                      >
                        {item.ticker}
                      </Link>
                    </td>

                    {/* LAST CLOSE */}
                    <td className="p-3 font-mono">
                      {item.last_close.toFixed(4)}
                    </td>

                    {/* RUNTIME PRICE */}
                    <td className="p-3 font-mono">
                      {item.runtime_price.toFixed(4)}
                    </td>

                    {/* DELTA */}
                    <td className={`p-3 font-mono ${deltaClass}`}>
                      {item.delta > 0 ? "+" : ""}{item.delta.toFixed(6)}
                    </td>

                    {/* PRED RETURN */}
                    <td className="p-3">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          (item.pred_return ?? 0) >= 0
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {(item.pred_return ?? 0) >= 0 ? "▲ " : "▼ "}{((item.pred_return ?? 0) * 100).toFixed(4)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

    </div>
  );
}
