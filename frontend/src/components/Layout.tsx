import type { ReactNode } from "react";
import Header from "./Header";

export default function Layout({
  left,
  right,
  runId,
  onRefresh,
}: {
  left: ReactNode;
  right: ReactNode;
  runId: string;
  onRefresh: () => void;
}) {
  return (
    <div className="min-h-screen bg-sky-50 p-6">

      {/* HEADER */}
      <div className="flex justify-between items-center mb-6">

        <h1 className="text-3xl font-bold">
          IE212 Stock Prediction Dashboard
        </h1>

        <Header runId={runId} onRefresh={onRefresh} />

      </div>

      {/* GRID */}
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-8">{left}</div>
        <div className="col-span-4 space-y-6">{right}</div>
      </div>

    </div>
  );
}