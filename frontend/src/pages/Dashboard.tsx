import { useEffect, useState } from "react";

type DashboardSummary = {
  latest_run_id: string;
  model_name: string;
  as_of_date: string;
  row_count: number;
  ticker_count: number;
  avg_pred_return: number;
  max_pred_return: number;
  min_pred_return: number;
  last_updated: string;
};

export default function Dashboard() {
    const [data, setData] = useState<DashboardSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetch("http://localhost:8008/dashboard/summary")
        .then((res) => {
            if (!res.ok) {
            throw new Error("Failed to fetch dashboard data");
            }
            return res.json();
        })
        .then((json) => {
            setData(json);
            setLoading(false);
        })
        .catch((err) => {
            setError(err.message);
            setLoading(false);
        });
    }, []);

    if (loading) return <p>Loading dashboard...</p>;
    if (error) return <p>Error: {error}</p>;
    if (!data) return null;

    return (
    <div className="bg-gray-100 p-8">
        <h1 className="text-4xl font-bold mb-6">Dashboard Overview</h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-xl p-4">
            <p className="text-gray-500">Latest Run</p>
            <p className="font-semibold">{data.latest_run_id}</p>
        </div>

        <div className="bg-white shadow rounded-xl p-4">
            <p className="text-gray-500">Model</p>
            <p className="font-semibold">{data.model_name}</p>
        </div>

        <div className="bg-white shadow rounded-xl p-4">
            <p className="text-gray-500">Tickers</p>
            <p className="font-semibold">{data.ticker_count}</p>
        </div>

        <div className="bg-white shadow rounded-xl p-4">
            <p className="text-gray-500">Avg Return</p>
            <p className="font-semibold">
            {data.avg_pred_return.toFixed(6)}
            </p>
        </div>
        </div>
    </div>
    );
}