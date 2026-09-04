import { useState } from "react";
import { matchCandidates } from "../api.js";

export default function JobMatch() {
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [searching, setSearching] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!jobDescription.trim()) {
      setError("Paste a job description to search against.");
      return;
    }
    setError("");
    setSearching(true);
    try {
      setResult(await matchCandidates(jobDescription));
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <section className="card">
      <h2>Find Best-Fit Candidates</h2>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="job-description">Job description</label>
          <textarea
            id="job-description"
            rows={6}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here…"
          />
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={searching}>
          {searching ? "Searching…" : "Find Matches"}
        </button>
      </form>

      {result && (
        <div className="match-output">
          {result.job_description_skills.length > 0 && (
            <div className="field">
              <label>Skills detected in this job description</label>
              <div className="skill-chips">
                {result.job_description_skills.map((skill) => (
                  <span className="skill-chip" key={skill}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.note && <p className="notice">{result.note}</p>}

          {result.excluded_count > 0 && (
            <p className="hint">
              {result.excluded_count} candidate(s) excluded — skills not yet reviewed.
            </p>
          )}

          {result.results.length === 0 && !result.note && (
            <p className="empty">No candidates with reviewed skills yet.</p>
          )}

          {result.results.length > 0 && (
            <ol className="match-list">
              {result.results.map((match, index) => (
                <li className="match-row" key={match.id}>
                  <div className="match-row-header">
                    <span className="match-rank">#{index + 1}</span>
                    <span className="match-name">{match.candidate_name}</span>
                    <span className="match-percentage">{match.match_percentage}% match</span>
                  </div>
                  <div className="hint">{match.original_filename}</div>
                  {match.matched_skills.length > 0 && (
                    <div className="skill-chips">
                      {match.matched_skills.map((skill) => (
                        <span className="skill-chip" key={skill}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                  {match.missing_skills.length > 0 && (
                    <div className="skill-chips">
                      {match.missing_skills.map((skill) => (
                        <span className="skill-chip skill-chip-missing" key={skill}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}
