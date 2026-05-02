import { useEffect, useState } from "react";

type Summary = {
  latest_run_id: string;
  ticker_count: number;
  avg_pred_return: number;
  last_updated: string;
};

type Prediction = {
  ticker: string;
  pred_return: number;
};

export default function RunSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [topPositive, setTopPositive] = useState<string | null>(null);
  const [topNegative, setTopNegative] = useState<string | null>(null);

  useEffect(() => {
    // fetch summary
    fetch("http://localhost:8008/dashboard/summary")
      .then((res) => res.json())
      .then((data) => setSummary(data));

    // fetch latest predictions để tính top +/- 📊
    fetch("http://localhost:8008/predictions/runs/latest")
      .then((res) => res.json())
      .then((data) => {
        const items: Prediction[] = data.items ?? [];

        if (!items.length) return;

        const max = items.reduce((a, b) =>
          a.pred_return > b.pred_return ? a : b
        );

        const min = items.reduce((a, b) =>
          a.pred_return < b.pred_return ? a : b
        );

        setTopPositive(
          `${max.ticker} (${(max.pred_return * 100).toFixed(4)}%)`
        );

        setTopNegative(
          `${min.ticker} (${(min.pred_return * 100).toFixed(4)}%)`
        );
      });
  }, []);

  if (!summary) {
    return (
      <div className="bg-white shadow rounded-xl p-5">
        Loading summary...
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