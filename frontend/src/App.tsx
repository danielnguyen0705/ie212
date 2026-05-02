import { useState } from "react";
import { Routes, Route } from "react-router-dom";

import Layout from "./components/Layout";
import PredictionTable from "./pages/PredictionTable";
import RecentRuns from "./pages/RecentRuns";
import RunSummary from "./components/RunSummary";
import TickerDetail from "./pages/TickerDetail";
import Analytics from "./pages/Analytics";

export default function App() {
  const [selectedRunId, setSelectedRunId] = useState(
    "local_inference_20260416_180240"
  );

  const refreshDashboard = () => {
    window.location.reload();
  };

  return (
    <Routes>

      {/* DASHBOARD */}
      <Route
        path="/"
        element={
          <Layout
            runId={selectedRunId}
            onRefresh={refreshDashboard}
            left={<PredictionTable runId={selectedRunId} />}
            right={
              <>
                <RunSummary />
                <RecentRuns onSelectRun={setSelectedRunId} />
              </>
            }
          />
        }
      />

      <Route
        path="/analytics"
        element={
          <Analytics
            runId={selectedRunId}
            onRefresh={refreshDashboard}
            onSelectRun={setSelectedRunId}
          />
        }
      />

      {/* TICKER DETAIL PAGE */}
      <Route
        path="/ticker/:ticker"
        element={<TickerDetail />}
      />

    </Routes>
  );
}