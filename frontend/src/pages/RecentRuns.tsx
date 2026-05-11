import { useEffect, useState } from "react";
import { getRecentRuns, APIError } from "../api";
import ErrorBanner from "../components/ErrorBanner";

type Run = {
  run_id: string;
  as_of_date: string | null;
  model_name: string;
  row_count: number;
  first_created_at: string;
  last_created_at: string;
};

export default function RecentRuns({
  onSelectRun,
}: {
  onSelectRun: (runId: string) => void;
}) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getRecentRuns(10)
      .then((data) => {
        setRuns(data.items);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof APIError) {
          setError(err.detail || "Failed to fetch runs");
        } else {
          setError(err instanceof Error ? err.message : "Failed to fetch runs");
        }
        setLoading(false);
      });
  }, []);

  if (loading)
    return (
      <div className="bg-white shadow rounded-xl p-5">
        <p className="p-4 text-gray-500">Loading recent runs...</p>
      </div>
    );

  if (error)
    return (
      <>
        <ErrorBanner error={error} onClose={() => setError(null)} />
        <div className="bg-white shadow rounded-xl p-5">
          <p className="p-4 text-red-500">Error: {error}</p>
        </div>
      </>
    );

  if (runs.length === 0)
    return (
      <div className="bg-white shadow rounded-xl p-5">
        <p className="p-4 text-gray-400">No recent runs available</p>
      </div>
    );

  return (
    <div className="bg-white shadow rounded-xl p-5">
      <h2 className="font-semibold text-lg mb-4">Recent Runs</h2>

      <div className="space-y-3 max-h-[420px] overflow-y-auto">
        {runs.map((run) => (
          <div
            key={run.run_id}
            className="border rounded-lg p-3 hover:bg-gray-50 cursor-pointer transition"
            onClick={() => onSelectRun(run.run_id)}
          >
            <p className="font-semibold text-sm">
              {run.run_id}
            </p>

            <p className="text-xs text-gray-500">
              model = {run.model_name}
            </p>

            <p className="text-xs text-gray-500">
              as_of_date = {run.as_of_date}
            </p>

            <p className="text-xs text-gray-400">
              created ={" "}
              {new Date(run.last_created_at).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}