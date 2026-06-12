import { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";

import Layout from "./components/Layout";
import PredictionTable from "./pages/PredictionTable";
import RunSummary from "./components/RunSummary";
import TickerDetail from "./pages/TickerDetail";
import RealtimeChart from "./pages/RealtimeChart";
import AIDecision from "./pages/AIDecision";
import Statistics from "./components/Statistics";
import ErrorBanner from "./components/ErrorBanner";
import { getDashboardSummary } from "./api";

export default function App() {
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("predictions");

  const fetchSummary = () => {
    getDashboardSummary()
      .then((data) => {
        if (data && data.latest_run_id) {
          setSelectedRunId(data.latest_run_id);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch latest run_id:", err);
        setGlobalError("Không thể kết nối với Backend API. Vui lòng đảm bảo dịch vụ đang chạy.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchSummary();
    const interval = setInterval(fetchSummary, 5000);
    return () => clearInterval(interval);
  }, []);

  const refreshDashboard = () => {
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
          <div className="text-lg font-medium text-slate-600">Đang tải giao diện hệ thống...</div>
        </div>
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case "predictions":
        return (
          <Layout
            runId={selectedRunId}
            onRefresh={refreshDashboard}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            left={<PredictionTable runId={selectedRunId} />}
            right={<RunSummary />}
          />
        );
      case "stream":
        return (
          <Layout
            runId={selectedRunId}
            onRefresh={refreshDashboard}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            left={<RealtimeChart />}
            right={<RunSummary />}
          />
        );
      case "ai":
        return (
          <Layout
            runId={selectedRunId}
            onRefresh={refreshDashboard}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            left={<AIDecision />}
            right={<RunSummary />}
          />
        );
      case "analytics":
        return (
          <Layout
            runId={selectedRunId}
            onRefresh={refreshDashboard}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            left={<Statistics runId={selectedRunId} />}
            right={<RunSummary />}
          />
        );
      default:
        return null;
    }
  };

  return (
    <>
      <ErrorBanner error={globalError} onClose={() => setGlobalError(null)} />
      <Routes>
        <Route path="/" element={renderTabContent()} />
        <Route path="/ticker/:ticker" element={<TickerDetail />} />
      </Routes>
    </>
  );
}
