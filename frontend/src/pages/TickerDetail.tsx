import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";

type PriceRow = {
  date: string;
  close: number;
};

type PredictionRow = {
  run_id: string;
  pred_close: number;
  pred_return: number;
  created_at: string;
};

export default function TickerDetail() {
  const { ticker } = useParams();

  const [priceHistory, setPriceHistory] = useState<PriceRow[]>([]);
  const [predictionHistory, setPredictionHistory] =
    useState<PredictionRow[]>([]);

  useEffect(() => {
    fetch(
      `http://localhost:8008/prices/ticker/${ticker}/history`
    )
      .then((res) => res.json())
      .then((data) =>
        setPriceHistory(data.items ?? [])
      );

    fetch(
      `http://localhost:8008/predictions/ticker/${ticker}/history`
    )
      .then((res) => res.json())
      .then((data) =>
        setPredictionHistory(data.items ?? [])
      );
  }, [ticker]);

  /**
   * FIX: prediction history không cùng date với price history
   * nên dùng latest prediction làm horizontal reference line
   */
  const latestPred =
    predictionHistory.length > 0
      ? predictionHistory[0].pred_close
      : null;

  const mergedChartData = priceHistory.map((p) => ({
    date: p.date,
    close: p.close,
    pred_close: latestPred,
  }));

  return (
    <div className="min-h-screen bg-slate-50 p-6 space-y-6">

      {/* BACK BUTTON */}
      <Link
        to="/"
        className="inline-block px-5 py-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:bg-gray-50 transition" style={{ backgroundColor: "#99fa99" }}
      >
        Back to Dashboard
      </Link>

      {/* TITLE */}
      <h1 className="text-2xl font-bold">
        Ticker Detail — {ticker}
      </h1>

      {/* COMPARISON CHART */}
      <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">

        <h2 className="font-semibold mb-4">
          Actual vs Predicted Price
        </h2>

        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mergedChartData}>
              <CartesianGrid strokeDasharray="3 3" />

              <XAxis dataKey="date" />

              <YAxis />

              <Tooltip />

              <Legend />

              {/* ACTUAL PRICE */}
              <Line
                type="monotone"
                dataKey="close"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
                name="Actual Price"
              />

              {/* PREDICTED PRICE */}
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

      {/* TWO TABLES */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* PRICE HISTORY */}
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">

          <h2 className="font-semibold mb-4">
            Price History
          </h2>

          <div className="overflow-auto max-h-[420px]">

            <table className="w-full text-sm">

              <thead className="text-xs uppercase tracking-wide text-gray-400 border-b">

                <tr>
                  <th className="p-3 text-left">
                    Date
                  </th>
                  <th className="p-3 text-left">
                    Close
                  </th>
                </tr>

              </thead>

              <tbody>

                {priceHistory.map((row) => (
                  <tr
                    key={row.date}
                    className="border-b hover:bg-slate-50 transition"
                  >
                    <td className="p-3">
                      {row.date}
                    </td>

                    <td className="p-3 font-medium">
                      {row.close.toFixed(2)}
                    </td>
                  </tr>
                ))}

              </tbody>

            </table>

          </div>

        </div>


        {/* PREDICTION HISTORY */}
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-6">

          <h2 className="font-semibold mb-4">
            Prediction History
          </h2>

          <div className="overflow-auto max-h-[420px]">

            <table className="w-full text-sm">

              <thead className="text-xs uppercase tracking-wide text-gray-400 border-b">

                <tr>
                  <th className="p-3 text-left">
                    Run ID
                  </th>
                  <th className="p-3 text-left">
                    Pred Close
                  </th>
                  <th className="p-3 text-left">
                    Return %
                  </th>
                </tr>

              </thead>

              <tbody>

                {predictionHistory.map((row) => (
                  <tr
                    key={row.run_id}
                    className="border-b hover:bg-slate-50 transition"
                  >
                    <td className="p-3">
                      {row.run_id}
                    </td>

                    <td className="p-3 font-medium">
                      {row.pred_close.toFixed(2)}
                    </td>

                    <td className="p-3">

                      <span
                        className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          row.pred_return >= 0
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {(row.pred_return * 100).toFixed(4)}%
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