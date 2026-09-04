const BASE = "/api/cvs";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response had no JSON body
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function listCVs() {
  return fetch(BASE).then(handle);
}

export function uploadCV(file, candidateName) {
  const form = new FormData();
  form.append("file", file);
  form.append("candidate_name", candidateName);
  return fetch(BASE, { method: "POST", body: form }).then(handle);
}

export function updateCV(id, { candidateName, file } = {}) {
  const form = new FormData();
  if (candidateName !== undefined) form.append("candidate_name", candidateName);
  if (file) form.append("file", file);
  return fetch(`${BASE}/${id}`, { method: "PUT", body: form }).then(handle);
}

export function deleteCV(id) {
  return fetch(`${BASE}/${id}`, { method: "DELETE" }).then(handle);
}

export function fileUrl(id) {
  return `${BASE}/${id}/file`;
}

export function getSkillSuggestions(id) {
  return fetch(`${BASE}/${id}/skills/suggestions`).then(handle);
}

export function saveSkills(id, skills) {
  return fetch(`${BASE}/${id}/skills`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ skills }),
  }).then(handle);
}

export function matchCandidates(jobDescription) {
  return fetch("/api/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription }),
  }).then(handle);
}
