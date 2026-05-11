import { useEffect, useState } from "react";
import { getDashboardSummary, getLatestPredictions, APIError } from "../api";
import ErrorBanner from "./ErrorBanner";

type Summary = {
  latest_run_id: string;
  ticker_count: number;
  avg_pred_return: number;
  last_updated: string;
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
    setLoading(true);
    setError(null);

    // fetch summary
    getDashboardSummary()
      .then((data) => setSummary(data))
      .catch((err) => {
        if (err instanceof APIError) {
          setError(err.detail || "Failed to load summary");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load summary");
        }
      });

    // fetch latest predictions untuk tính top +/- 📊
    getLatestPredictions()
      .then((data) => {
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
        // Silent fail for predictions, as summary is more important
        console.error("Failed to load predictions for top/bottom", err);
      })
      .finally(() => {
        setLoading(false);
      });
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
        <div className="text-gray-500 text-sm">Loading summary...</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-white shadow rounded-xl p-5">
        <p className="text-gray-400 text-sm">No summary data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-xl p-5 space-y-3">
      <h2 className="font-semibold text-lg">
        Run Summary
      </h2>

      <SummaryRow
        label="Latest Run"
        value={summary.latest_run_id}
      />

      <SummaryRow
        label="Ticker Count"
        value={summary.ticker_count.toString()}
      />

      <SummaryRow
        label="Avg Pred Return"
        value={`${(summary.avg_pred_return * 100).toFixed(4)}%`}
        highlight
      />

      <SummaryRow
        label="Last Updated"
        value={new Date(summary.last_updated).toLocaleString()}
      />

      {topPositive && (
        <SummaryRow
          label="Top Positive"
          value={topPositive}
          positive
        />
      )}

      {topNegative && (
        <SummaryRow
          label="Top Negative"
          value={topNegative}
          negative
        />
      )}
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