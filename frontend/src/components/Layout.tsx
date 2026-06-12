import type { ReactNode } from "react";
import Header from "./Header";

export default function Layout({
  left,
  right,
  runId,
  onRefresh,
  activeTab,
  onTabChange,
  bottom,
}: {
  left: ReactNode;
  right: ReactNode;
  runId: string;
  onRefresh: () => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
  bottom?: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* HEADER */}
        <div className="flex justify-between items-center bg-white p-5 rounded-2xl shadow-sm border">
          <h1 className="text-2xl font-black text-slate-800 tracking-tight">
            HỆ THỐNG DỰ BÁO GIÁ ĐÓNG CỔ PHIẾU
          </h1>
          <Header runId={runId} onRefresh={onRefresh} />
        </div>

        {/* TAB BAR */}
        <div className="flex flex-wrap gap-2 bg-slate-100 p-1.5 rounded-xl border w-fit">
          <button
            onClick={() => onTabChange("predictions")}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
              activeTab === "predictions"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-600 hover:text-slate-800"
            }`}
          >
            Bảng Thống Kê
          </button>
          <button
            onClick={() => onTabChange("stream")}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
              activeTab === "stream"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-600 hover:text-slate-800"
            }`}
          >
            Biểu Đồ Thời Gian Thực
          </button>
          <button
            onClick={() => onTabChange("analytics")}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
              activeTab === "analytics"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-600 hover:text-slate-800"
            }`}
          >
            Phân Tích Thống Kê
          </button>
          <button
            onClick={() => onTabChange("ai")}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
              activeTab === "ai"
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-600 hover:text-slate-800"
            }`}
          >
            Phân tích chi tiết các cổ phiếu
          </button>
        </div>

        {/* MAIN GRID */}
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-8">{left}</div>
          <div className="col-span-12 lg:col-span-4">{right}</div>
        </div>

        {/* STATISTICS SECTION */}
        {bottom && <div className="w-full">{bottom}</div>}
      </div>
    </div>
  );
}
