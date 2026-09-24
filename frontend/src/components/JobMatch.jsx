import { useState } from "react";
import { estimateMatch, matchCandidates } from "../api.js";
import HowItWorks from "./HowItWorks.jsx";

const fmtTokens = (n) => n.toLocaleString();
const fmtUsd = (n) => `$${n < 0.01 ? n.toFixed(4) : n.toFixed(3)}`;

export default function JobMatch() {
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [searching, setSearching] = useState(false);
  const [useAi, setUseAi] = useState(false);
  // Token preview shown before an AI search: { data } on success or { error } if the estimate failed.
  const [estimate, setEstimate] = useState(null);
  const [estimating, setEstimating] = useState(false);

  async function runSearch() {
    setEstimate(null);
    setError("");
    setSearching(true);
    try {
      setResult(await matchCandidates(jobDescription, useAi));
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!jobDescription.trim()) {
      setError("Paste a job description to search against.");
      return;
    }
    if (!useAi) {
      await runSearch();
      return;
    }
    // AI on: preview the token cost first; the search runs only after the user confirms.
    setError("");
    setEstimating(true);
    try {
      const data = await estimateMatch(jobDescription);
      if (data.candidate_count === 0) {
        await runSearch();
        return;
      }
      setEstimate({ data });
    } catch (err) {
      setEstimate({ error: err.message });
    } finally {
      setEstimating(false);
    }
  }

  function handleDescriptionChange(value) {
    setJobDescription(value);
    setEstimate(null);
  }

  function handleToggle(checked) {
    setUseAi(checked);
    setEstimate(null);
  }

  const busy = searching || estimating;

  return (
    <section className="card">
      <HowItWorks title="Find Best-Fit Candidates" panelId="match-help">
        <p className="help-callout">
          <strong>AI is optional and off by default.</strong> With the toggle off, matching runs entirely on this
          computer. With it on, only each candidate&apos;s <em>reviewed skill names</em> and the job description you
          paste are sent to Claude, never CV text, candidate names or files.
        </p>
        <ol>
          <li>
            <strong>Who is included:</strong> only candidates whose skills have been reviewed and saved. Candidates
            with no saved skills are left out, and the results show how many were skipped (e.g. &quot;2 candidate(s)
            excluded — skills not yet reviewed&quot;). Use <em>Review Skills</em> on them to include them.
          </li>
          <li>
            <strong>Keyword matching (toggle off):</strong> local parsing rules find skills from the built-in
            quality-engineering list in the job description. Candidates are ranked by how many of those exact skills
            they have. Instant and free, but different wording or related skills aren&apos;t recognised.
          </li>
          <li>
            <strong>AI matching (toggle on):</strong> you first see a token and cost estimate, and nothing is sent until
            you click <em>Run AI search</em>. Claude then works out the skills the job needs, even when they&apos;re
            phrased differently, and scores every candidate 0–100 with a short reason. Related skills get partial
            credit.
          </li>
          <li>
            <strong>Results:</strong> candidates are ranked by score. Matched skills are shown normally and missing
            ones are crossed out. After an AI search, the tokens and cost actually used are shown.
          </li>
          <li>
            <strong>Fallback:</strong> if the AI can&apos;t be reached (e.g. missing API key or network problem), you
            get keyword results with a notice instead.
          </li>
        </ol>
        <p className="hint">
          The AI only knows each candidate by an internal id and their skill list, so the quality of the ranking
          depends on how complete the reviewed skills are.
        </p>
      </HowItWorks>
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="job-description">Job description</label>
          <textarea
            id="job-description"
            rows={6}
            value={jobDescription}
            onChange={(e) => handleDescriptionChange(e.target.value)}
            placeholder="Paste the job description here…"
          />
        </div>
        <label className="toggle">
          <input type="checkbox" checked={useAi} onChange={(e) => handleToggle(e.target.checked)} />
          Use Claude AI for matching
          <span className="hint">
            {useAi ? "Claude reads the description and ranks candidates." : "Keyword matching only — no API call."}
          </span>
        </label>
        {error && <p className="error">{error}</p>}
        {!estimate && (
          <button type="submit" disabled={busy}>
            {estimating ? "Estimating…" : searching ? (useAi ? "Analyzing…" : "Searching…") : "Find Matches"}
          </button>
        )}
      </form>

      {estimate && (
        <div className="estimate">
          {estimate.data ? (
            <>
              <p className="estimate-title">Estimated usage for this AI search</p>
              <ul className="estimate-lines">
                <li>
                  <strong>{fmtTokens(estimate.data.input_tokens)}</strong> input tokens (exact)
                </li>
                <li>
                  <strong>
                    ~{fmtTokens(estimate.data.output_tokens_low)}–{fmtTokens(estimate.data.output_tokens_high)}
                  </strong>{" "}
                  output tokens (estimated)
                </li>
                <li>
                  ≈ {fmtUsd(estimate.data.cost_usd_low)}–{fmtUsd(estimate.data.cost_usd_high)} ·{" "}
                  {estimate.data.candidate_count} candidate(s) · {estimate.data.model}
                </li>
              </ul>
            </>
          ) : (
            <p className="error">{estimate.error}</p>
          )}
          <div className="estimate-actions">
            <button type="button" onClick={runSearch} disabled={busy}>
              {searching ? "Analyzing…" : estimate.data ? "Run AI search" : "Run anyway"}
            </button>
            <button type="button" className="secondary" onClick={() => setEstimate(null)} disabled={busy}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="match-output">
          {result.job_description_skills.length > 0 && (
            <div className="field">
              <label>Skills required by this job</label>
              <div className="skill-chips">
                {result.job_description_skills.map((skill) => (
                  <span className="skill-chip" key={skill}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.engine === "llm" && (
            <p className="hint">
              AI-ranked using each candidate's reviewed skills.
              {result.usage &&
                ` Used ${fmtTokens(result.usage.input_tokens)} input + ${fmtTokens(result.usage.output_tokens)} output tokens (≈ ${fmtUsd(result.usage.cost_usd)}).`}
            </p>
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
                  {match.reasoning && <p className="match-reasoning">{match.reasoning}</p>}
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
