import Layout from "../components/Layout";
import RunSummary from "../components/RunSummary";
import RecentRuns from "./RecentRuns";
import Statistics from "../components/Statistics";

type AnalyticsProps = {
  runId: string;
  onRefresh: () => void;
  onSelectRun: (runId: string) => void;
};

export default function Analytics({ runId, onRefresh, onSelectRun }: AnalyticsProps) {
  return (
    <Layout
      runId={runId}
      onRefresh={onRefresh}
      left={<Statistics runId={runId} />}
      right={
        <>
          <RunSummary />
          <RecentRuns onSelectRun={onSelectRun} />
        </>
      }
    />
  );
}
