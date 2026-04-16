import { useEffect, useState } from "react";

type Run = {
  run_id: string;
  as_of_date: string;
  model_name: string;
  row_count: number;
  first_created_at: string;
  last_created_at: string;
};

type Response = {
  count: number;
  items: Run[];
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
    fetch("http://localhost:8008/predictions/runs/recent")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch runs");
        return res.json();
      })
      .then((data: Response) => {
        setRuns(data.items);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading)
    return <p className="p-4 text-gray-500">Loading recent runs...</p>;

  if (error)
    return (
      <p className="p-4 text-red-500">
        Error loading runs: {error}
      </p>
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