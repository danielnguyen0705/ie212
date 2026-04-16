import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

type Prediction = {
  ticker: string;
  last_close: number;
  pred_close: number;
  pred_return: number;
  graph_gate?: number;
  created_at?: string;
};

type PredictionResponse = {
  run_id: string;
  as_of_date: string;
  model_name: string;
  row_count: number;
  items: Prediction[];
};

export default function PredictionTable({
  runId,
}: {
  runId: string;
}) {
  const [data, setData] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setLoading(true);

    fetch(`http://localhost:8008/predictions/runs/${runId}`)
      .then((res) => res.json())
      .then((json: PredictionResponse) => {
        setData(json.items ?? []);
        setLoading(false);
      });
  }, [runId]);

  const filtered = data.filter((item) =>
    item.ticker.toLowerCase().includes(filter.toLowerCase())
  );

  if (loading) {
    return (
      <div className="bg-white shadow rounded-xl p-6">
        Loading predictions...
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-xl p-6">

      {/* HEADER */}
      <div className="flex justify-between items-center mb-4">

        <h2 className="text-xl font-semibold">
          Predictions — {runId}
        </h2>

        <div className="text-sm text-gray-500">
          Showing {filtered.length} / {data.length} rows
        </div>

      </div>

      {/* FILTER */}
      <input
        type="text"
        placeholder="Filter ticker..."
        className="border rounded-lg px-4 py-2 mb-4 w-full max-w-xs"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />

      {/* TABLE */}
      <div className="overflow-auto max-h-[420px]">

        <table className="w-full text-sm">

          <thead className="text-gray-500 border-b">
            <tr>
              <th className="p-3 text-left">Ticker</th>
              <th className="p-3 text-left">Last Close</th>
              <th className="p-3 text-left">Pred Close</th>
              <th className="p-3 text-left">Delta</th>
              <th className="p-3 text-left">Pred Return (%)</th>
              <th className="p-3 text-left">Graph Gate</th>
              <th className="p-3 text-left">Created At</th>
            </tr>
          </thead>

          <tbody>

            {filtered.map((item) => {
              const delta =
                item.pred_close - item.last_close;

              return (
                <tr
                  key={item.ticker}
                  className="border-b hover:bg-gray-50"
                >

                  {/* TICKER (FIXED LINK) */}
                  <td className="p-3 font-semibold text-blue-600">
                    <Link
                      to={`/ticker/${item.ticker}`}
                      className="hover:underline"
                    >
                      {item.ticker}
                    </Link>
                  </td>

                  {/* LAST CLOSE */}
                  <td className="p-3">
                    {item.last_close.toFixed(4)}
                  </td>

                  {/* PRED CLOSE */}
                  <td className="p-3">
                    {item.pred_close.toFixed(4)}
                  </td>

                  {/* DELTA */}
                  <td
                    className={`p-3 font-semibold ${
                      delta >= 0
                        ? "text-green-600"
                        : "text-red-600"
                    }`}
                  >
                    {delta.toFixed(6)}
                  </td>

                  {/* RETURN BADGE */}
                  <td className="p-3">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        item.pred_return >= 0
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {(item.pred_return * 100).toFixed(4)}%
                    </span>
                  </td>

                  {/* GRAPH GATE */}
                  <td className="p-3">
                    {item.graph_gate?.toFixed(4) ?? "0.0000"}
                  </td>

                  {/* CREATED AT */}
                  <td className="p-3 text-gray-500">
                    {item.created_at
                      ? new Date(
                          item.created_at
                        ).toLocaleString()
                      : "-"}
                  </td>

                </tr>
              );
            })}

          </tbody>

        </table>

      </div>

    </div>
  );
}