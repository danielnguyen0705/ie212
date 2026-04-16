import { useState } from "react";

export default function Header({
  runId,
  onRefresh,
}: {
  runId: string;
  onRefresh: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);

  // COPY RUN ID
  const copyRunId = () => {
    navigator.clipboard.writeText(runId);
    setCopied(true);
  };

  // CHECK API HEALTH
  const checkHealth = async () => {
    try {
      const res = await fetch("http://localhost:8008/health");
      setHealthy(res.ok);
    } catch {
      setHealthy(false);
    }
  };

  return (
    <div className="flex items-center gap-3">

      {/* CHECK API */}
      <button
        onClick={checkHealth}
        className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 shadow-sm hover:shadow-md hover:scale-105 active:scale-95 ${
          healthy
            ? "bg-green-200 text-green-800 hover:bg-green-300"
            : "bg-gray-200 text-gray-700 hover:bg-gray-300"
        }`}
      >
        {healthy ? "API Healthy" : "Check API"}
      </button>

      {/* REFRESH */}
      <button
        onClick={onRefresh}
        className="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-all duration-200 shadow-sm hover:shadow-md hover:scale-105 active:scale-95"
      >
        Refresh
      </button>

      {/* COPY RUN ID */}
      <button
        onClick={copyRunId}
        className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 shadow-sm hover:shadow-md hover:scale-105 active:scale-95 ${
          copied
            ? "bg-blue-100 text-blue-600"
            : "bg-gray-200 hover:bg-gray-300"
        }`}
      >
        {copied ? "Copied" : "Copy Run ID"}
      </button>

      {/* OPEN API DOCS */}
      <button
        onClick={() =>
          window.open("http://localhost:8008/docs", "_blank")
        }
        className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-gray-800 transition-all duration-200 shadow-sm hover:shadow-md hover:scale-105 active:scale-95"
      >
        Open API Docs
      </button>

    </div>
  );
}