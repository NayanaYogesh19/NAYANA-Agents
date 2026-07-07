const BASE = "/api";

export async function startRun({ companyUrl, start, end }) {
  const res = await fetch(`${BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_url: companyUrl, start, end }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json(); // { job_id }
}

export async function getRun(jobId) {
  const res = await fetch(`${BASE}/runs/${jobId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json(); // JobStatusOut
}
