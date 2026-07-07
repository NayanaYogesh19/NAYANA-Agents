import { useEffect, useRef, useState } from "react";
import Topbar from "./components/Topbar";
import RunForm from "./components/RunForm";
import ProgressPanel from "./components/ProgressPanel";
import ResultsView from "./components/ResultsView";
import { useTheme } from "./lib/useTheme";
import { startRun, getRun } from "./lib/api";

const POLL_MS = 3000;

function App() {
  const { theme, toggle } = useTheme();
  const [jobId, setJobId] = useState(() => new URLSearchParams(window.location.search).get("job"));
  const [job, setJob] = useState(null);
  const [submitError, setSubmitError] = useState("");
  const pollRef = useRef(null);

  const isRunning = job?.status === "pending" || job?.status === "running";

  useEffect(() => {
    if (!jobId) return;

    async function poll() {
      try {
        const data = await getRun(jobId);
        setJob(data);
        if (data.status === "done" || data.status === "error") {
          clearInterval(pollRef.current);
        }
      } catch (err) {
        setJob({ status: "error", error: err.message, stage: "" });
        clearInterval(pollRef.current);
      }
    }

    poll();
    pollRef.current = setInterval(poll, POLL_MS);
    return () => clearInterval(pollRef.current);
  }, [jobId]);

  async function handleSubmit({ companyUrl, start, end }) {
    setSubmitError("");
    setJob(null);
    try {
      const { job_id } = await startRun({ companyUrl, start, end });
      setJobId(job_id);
      setJob({ status: "pending", stage: "Queued" });
      const url = new URL(window.location.href);
      url.searchParams.set("job", job_id);
      window.history.replaceState({}, "", url);
    } catch (err) {
      setSubmitError(err.message);
    }
  }

  return (
    <div className="app-outer" style={{ minHeight: "100vh", display: "flex", justifyContent: "center", padding: "1rem" }}>
      <div className="atmosphere" />
      <div
        className="app-shell glass-panel"
        style={{
          width: "100%",
          maxWidth: 1100,
          borderRadius: "2rem",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Topbar theme={theme} onToggleTheme={toggle} />

        <div className="app-main page-enter" style={{ padding: "1.5rem 2rem 3rem", overflowY: "auto" }}>
          <div className="flex flex-col gap-5" style={{ maxWidth: 900, margin: "0 auto" }}>
            <RunForm onSubmit={handleSubmit} disabled={isRunning} />

            {submitError && (
              <div className="glass-card-static p-4" style={{ color: "var(--status-danger)", fontSize: "0.85rem" }}>
                {submitError}
              </div>
            )}

            {job && (isRunning || job.status === "error") && (
              <ProgressPanel stage={job.stage} error={job.status === "error" ? job.error : null} />
            )}

            {job?.status === "done" && job.report && <ResultsView report={job.report} />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
