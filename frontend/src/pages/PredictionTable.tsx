import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRunDetail, APIError, type PredictionItem } from "../api";
import ErrorBanner from "../components/ErrorBanner";

export default function PredictionTable({
  runId,
}: {
  runId: string;
}) {
  const [data, setData] = useState<PredictionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    setError(null);

    getRunDetail(runId)
      .then((json) => {
        setData(json.items ?? []);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof APIError) {
          setError(
            err.status === 404
              ? `Run not found: ${runId}`
              : err.detail || "Failed to load predictions"
          );
        } else {
          setError(err instanceof Error ? err.message : "Failed to load predictions");
        }
        setLoading(false);
      });
  }, [runId]);

  const filtered = data.filter((item) =>
    item.ticker.toLowerCase().includes(filter.toLowerCase())
  );

  if (error) {
    return (
      <>
        <ErrorBanner error={error} onClose={() => setError(null)} />
        <div className="bg-white shadow rounded-xl p-6 text-center py-12">
          <p className="text-red-600 font-medium">Error: {error}</p>
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <div className="bg-white shadow rounded-xl p-6">
        <div className="text-center py-8 text-gray-500">
          Loading predictions...
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white shadow rounded-xl p-6 text-center py-12">
        <p className="text-gray-400">No predictions found for this run.</p>
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
        {filtered.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            No predictions match filter "{filter}"
          </div>
        ) : (
          <table className="w-full text-sm">

          <thead className="text-gray-500 border-b">
            <tr>
              <th className="p-3 text-left">Ticker</th>
              <th className="p-3 text-left">Last Close</th>
              <th className="p-3 text-left">Pred Close</th>
              <th className="p-3 text-left">Delta</th>
              <th className="p-3 text-left">Pred Return (%)</th>
              <th className="p-3 text-left">Confidence</th>
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
                        (item.pred_return ?? 0) >= 0
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {((item.pred_return ?? 0) * 100).toFixed(4)}%
                    </span>
                  </td>

                  {/* GRAPH GATE - CONFIDENCE BADGE */}
                  <td className="p-3">
                    {(() => {
                      const confidence = item.graph_gate ?? 0;
                      const bgColor =
                        confidence > 0.6
                          ? "bg-green-100 text-green-700"
                          : confidence >= 0.3
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700";
                      const label =
                        confidence > 0.6
                          ? "High"
                          : confidence >= 0.3
                          ? "Medium"
                          : "Low";
                      return (
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${bgColor}`}
                        >
                          {label} ({confidence.toFixed(3)})
                        </span>
                      );
                    })()}
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
        )}
      </div>

    </div>
  );
}