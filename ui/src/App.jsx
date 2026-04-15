import { useEffect, useMemo, useState } from "react";

const mode = import.meta.env.VITE_CIEM_MODE || "local";
const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const mcpBase = import.meta.env.VITE_MCP_BASE_URL || "http://localhost:8001";

const stages = [
  "Create analysis job",
  "Upload artifacts and governance docs",
  "Build permission graph",
  "Generate candidate policy",
  "Validate and diff",
  "Explain decisions and export bundle"
];

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [projectId, setProjectId] = useState("proj-123");
  const [jobName, setJobName] = useState("payments-api-rightsizing");
  const [selectedJobId, setSelectedJobId] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId),
    [jobs, selectedJobId]
  );

  async function fetchJobs() {
    const response = await fetch(`${apiBase}/v1/jobs`);
    if (!response.ok) {
      throw new Error("Could not load jobs.");
    }
    const data = await response.json();
    setJobs(data);
    if (!selectedJobId && data.length > 0) {
      setSelectedJobId(data[0].id);
    }
  }

  useEffect(() => {
    fetchJobs().catch(() => {
      setMessage("API is unavailable. Start the local stack first.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreateJob(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBase}/v1/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: jobName,
          project_id: projectId,
          target_providers: ["aws"],
          mode: "design_time"
        })
      });
      if (!response.ok) {
        throw new Error("Failed to create job.");
      }
      const job = await response.json();
      await fetchJobs();
      setSelectedJobId(job.id);
      setMessage(`Created job ${job.id}`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRegisterPolicyDoc() {
    if (!selectedJobId) {
      setMessage("Select a job first.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBase}/v1/jobs/${selectedJobId}/policy-documents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Cloud Workload Least Privilege Standard",
          scope: "global",
          provider: "all",
          priority: 100,
          content_type: "markdown",
          content: "No workload identity may modify IAM roles."
        })
      });
      if (!response.ok) {
        throw new Error("Failed to register policy document.");
      }
      await fetchJobs();
      setMessage("Registered governance document and advanced job state.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleBuildGraph() {
    if (!selectedJobId) {
      setMessage("Select a job first.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBase}/v1/jobs/${selectedJobId}/build-permission-graph`, {
        method: "POST"
      });
      const data = await response.json();
      if (!response.ok) {
        const errorCode = data?.detail?.error?.code || "UNKNOWN_ERROR";
        throw new Error(`Build graph failed: ${errorCode}`);
      }
      await fetchJobs();
      setMessage(`Graph built (${data.node_count} nodes / ${data.edge_count} edges).`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="card">
        <h1>CIEM Factory</h1>
        <p>Least-privilege rightsizing for cloud identities through MCP.</p>
        <div className="row">
          <span className="badge">Mode: {mode}</span>
          <span className="badge">API: {apiBase}</span>
          <span className="badge">MCP: {mcpBase}</span>
        </div>
      </header>

      <section className="grid">
        <article className="card">
          <h2>Interactive Demo</h2>
          <form className="form" onSubmit={handleCreateJob}>
            <label>
              Project ID
              <input value={projectId} onChange={(event) => setProjectId(event.target.value)} />
            </label>
            <label>
              Job Name
              <input value={jobName} onChange={(event) => setJobName(event.target.value)} />
            </label>
            <button type="submit" disabled={loading}>Create Job</button>
          </form>
          <div className="row">
            <select
              value={selectedJobId}
              onChange={(event) => setSelectedJobId(event.target.value)}
            >
              <option value="">Select job</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.id} ({job.status})
                </option>
              ))}
            </select>
            <button type="button" onClick={handleRegisterPolicyDoc} disabled={loading || !selectedJobId}>
              Register Policy Doc
            </button>
            <button type="button" onClick={handleBuildGraph} disabled={loading || !selectedJobId}>
              Build Graph
            </button>
          </div>
          {selectedJob ? (
            <p className="muted">Current status: <strong>{selectedJob.status}</strong></p>
          ) : null}
          {message ? <p className="muted">{message}</p> : null}
        </article>

        <article className="card">
          <h2>MVP UI Flow</h2>
          <ol>
            {stages.map((stage) => (
              <li key={stage}>{stage}</li>
            ))}
          </ol>
        </article>

        <article className="card">
          <h2>Deployment Profiles</h2>
          <p>
            Use one codebase for hosted and local/private runs with environment
            driven configuration.
          </p>
          <ul>
            <li>Local profile: single-tenant, private deployment.</li>
            <li>Hosted profile: multi-tenant, OIDC-ready deployment.</li>
            <li>Container-first with Docker Compose and Kubernetes path.</li>
          </ul>
        </article>
      </section>
    </main>
  );
}
