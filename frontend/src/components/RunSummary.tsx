import { useEffect, useState } from "react";
import { getDashboardSummary, getLatestPredictions, APIError } from "../api";
import ErrorBanner from "./ErrorBanner";

type Summary = {
  latest_run_id: string;
  ticker_count: number;
  avg_pred_return: number;
  last_updated: string;
  model_name: string;
};

type Prediction = {
  ticker: string;
  pred_return: number | null;
};

export default function RunSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [topPositive, setTopPositive] = useState<string | null>(null);
  const [topNegative, setTopNegative] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const fetchSummaryData = () => {
      // fetch summary
      getDashboardSummary()
        .then((data: any) => {
          if (active) {
            setSummary(data);
          }
        })
        .catch((err) => {
          if (active) {
            if (err instanceof APIError) {
              setError(err.detail || "Không thể tải dữ liệu tổng quan");
            } else {
              setError(err instanceof Error ? err.message : "Không thể tải dữ liệu tổng quan");
            }
          }
        });

      // fetch latest predictions để tính top +/-
      getLatestPredictions()
        .then((data) => {
          if (!active) return;
          const items: Prediction[] = (data.items ?? []).map((p) => ({
            ...p,
            pred_return: p.pred_return ?? 0,
          }));

          if (!items.length) return;

          const max = items.reduce((a, b) =>
            (a.pred_return ?? 0) > (b.pred_return ?? 0) ? a : b
          );

          const min = items.reduce((a, b) =>
            (a.pred_return ?? 0) < (b.pred_return ?? 0) ? a : b
          );

          setTopPositive(
            `${max.ticker} (${((max.pred_return ?? 0) * 100).toFixed(4)}%)`
          );

          setTopNegative(
            `${min.ticker} (${((min.pred_return ?? 0) * 100).toFixed(4)}%)`
          );
        })
        .catch((err) => {
          console.error("Failed to load predictions for top/bottom", err);
        })
        .finally(() => {
          if (active) {
            setLoading(false);
          }
        });
    };

    setLoading(true);
    setError(null);
    fetchSummaryData();

    // Polling tổng quan mỗi 3 giây
    const interval = setInterval(fetchSummaryData, 3000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  if (error) {
    return (
      <>
        <ErrorBanner error={error} onClose={() => setError(null)} />
        <div className="bg-white shadow rounded-xl p-5">
          <p className="text-red-600 text-sm font-medium">{error}</p>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <div className="bg-white shadow rounded-xl p-5">
        <div className="text-gray-500 text-sm">Đang tải dữ liệu tổng quan...</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-white shadow rounded-xl p-5">
        <p className="text-gray-400 text-sm">Không có dữ liệu tổng quan</p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-xl p-5 space-y-3">
      <h2 className="font-semibold text-lg text-slate-800 border-b pb-2">
        Tổng quan phiên
      </h2>

      <SummaryRow
        label="Mô hình dự đoán"
        value={summary.model_name}
        highlight
      />

      <SummaryRow
        label="Mã định danh phiên"
        value={summary.latest_run_id}
      />

      <SummaryRow
        label="Số lượng cổ phiếu"
        value={summary.ticker_count.toString()}
      />

      <SummaryRow
        label="Tỷ suất sinh lời trung bình"
        value={`${(summary.avg_pred_return * 100).toFixed(4)}%`}
      />

      {topPositive && (
        <SummaryRow
          label="Cổ phiếu tăng mạnh nhất"
          value={topPositive}
          positive
        />
      )}

      {topNegative && (
        <SummaryRow
          label="Cổ phiếu giảm mạnh nhất"
          value={topNegative}
          negative
        />
      )}

      <SummaryRow
        label="Cập nhật cuối cùng"
        value={new Date(summary.last_updated).toLocaleString("vi-VN")}
      />
    </div>
  );
}

function SummaryRow({
  label,
  value,
  highlight,
  positive,
  negative,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  positive?: boolean;
  negative?: boolean;
}) {
  return (
    <div className="flex justify-between items-center bg-gray-50 px-4 py-2 rounded-lg border">
      <span className="text-gray-500 text-sm">
        {label}
      </span>
      <span
        className={`font-semibold ${
          highlight
            ? "text-blue-600"
            : positive
            ? "text-green-600"
            : negative
            ? "text-red-600"
            : "text-gray-800"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
