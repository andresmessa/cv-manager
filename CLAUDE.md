# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

CV Manager: a small web app for uploading, listing, updating, and deleting candidate CVs (PDF/DOC/DOCX), extracting quality-engineering skills from them, and ranking candidates against a free-text job description using Claude (with a keyword-matching fallback).

- **Backend**: Python + FastAPI, single-process, no database — metadata lives in a JSON file and files on local disk.
- **Frontend**: React + Vite, no state management library — all state lives in `App.jsx` and is passed down as props.

## Commands

### Backend (from `backend/`)

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

AI matching needs `ANTHROPIC_API_KEY` in the environment the backend is started from (set it as a Windows user environment variable; never commit it — `StartStop.txt` is tracked by git). Environment changes only apply to newly opened terminals, so restart the backend from a fresh terminal after changing the key. Without a valid key the app still runs and matching falls back to keywords.

API served at `http://localhost:8000`; interactive docs at `http://localhost:8000/docs`. There is no lint/test setup for the backend (no pytest, ruff, etc. configured) — verify changes by exercising the endpoints via `/docs` or the running frontend.

### Frontend (from `frontend/`)

```powershell
npm install
npm run dev      # dev server on http://localhost:5173, proxies /api to :8000
npm run build
npm run preview
```

There is no test runner or linter configured in `package.json` — verify UI changes by running the dev server against a running backend.

Both servers must be running simultaneously for the app to work end-to-end (see `StartStop.txt` for the exact two-terminal startup sequence used on this machine).

## Architecture

### Data flow and persistence (`backend/app/storage.py`)

- All CV metadata is a single JSON array in `backend/data/metadata.json`; the file is fully read, mutated, and rewritten on every write operation (`_read_all` / `_write_all`), guarded by one process-wide `threading.Lock`. There is no per-record locking or migration mechanism — schema changes to a CV record mean updating `_read_all`'s `setdefault` calls for backward compatibility with existing entries.
- Uploaded files are stored under `backend/data/uploads/` renamed to `{uuid4()}{ext}`; the original filename is kept only in metadata (`original_filename`), decoupled from the on-disk `stored_filename`. Replacing a file on update deletes the old blob and writes a new UUID-named one.
- A CV record: `id, candidate_name, original_filename, stored_filename, content_type, size, skills, uploaded_at, updated_at`.

### Skill extraction and matching (`backend/app/skills_extractor.py`)

- `SKILL_TAXONOMY` is a hand-maintained dict mapping canonical quality-engineering skill names (Six Sigma, ISO 9001, CMM, GD&T, etc.) to lists of alias patterns. Aliases starting with `\b` are treated as regexes matched against lowercased text; everything else is escaped and matched as a literal substring. Extending recognized skills means adding entries here. The taxonomy drives upload-time skill suggestions and the keyword fallback for matching.
- Text is pulled from PDFs via `pypdf` and from `.docx` via `python-docx` (paragraphs + table cells); legacy `.doc` and scanned/text-less PDFs are explicitly unsupported and surface a user-facing note instead of failing silently.
- Skill suggestions from upload/extraction are never auto-saved — they only become part of a CV's `skills` once the user confirms them through the skills-review flow (`PUT /api/cvs/{id}/skills`). Candidate matching (`POST /api/match`) only considers CVs whose `skills` array is non-empty ("reviewed"); unreviewed CVs are silently excluded and counted in `excluded_count`.

### LLM job matching (`backend/app/llm_matcher.py`)

Job matching was originally purely keyword-based: `extract_skills()` ran the taxonomy over the job description and candidates were ranked by the count of exact skill-name matches. That missed anything phrased outside the taxonomy ("keeping processes statistically in control" → SPC) and gave no credit for related skills. Matching now uses Claude to interpret the job description and rank candidates; the keyword matcher remains as an opt-out and a fallback.

**Flow of `POST /api/match`** (`match_candidates` in `main.py`):
1. Reject an empty description (400); split CVs into reviewed (non-empty `skills`) and excluded. With no reviewed CVs, return early — no API call.
2. If `use_ai` is `false`, return `_keyword_match(...)` directly.
3. Otherwise call `llm_matcher.rank_candidates(job_description, reviewed)`. On `LLMMatchError`, log a warning and return `_keyword_match(...)` with the note "AI matching unavailable — showing keyword-based results."
4. Map the rankings back onto CV records and sort by score desc, then name.

**The Claude call** (`rank_candidates`):
- Model `claude-sonnet-5`, `client.messages.parse(..., output_format=MatchAnalysis)` with adaptive thinking — one call per search, which both infers the required skills and ranks candidates. Typical latency is several seconds.
- Only candidate `id` + stored `skills` are sent (as JSON in the user message) — no names, filenames or CV text. Ranking is therefore based solely on the user-reviewed skills.
- `SYSTEM_PROMPT` tells Claude to use canonical skill names (reusing names that already appear in candidates' lists), score 0–100 on stored skills only, give partial credit for closely related skills, weigh core requirements over nice-to-haves, and include every candidate once. Tune ranking behaviour there.
- Structured output schema: `MatchAnalysis { required_skills, rankings: [CandidateRanking { candidate_id, fit_score, matched_skills, missing_skills, reasoning }] }`.
- Every failure is normalised to `LLMMatchError`: SDK errors (`anthropic.AnthropicError`: auth, network, rate limit), a `TypeError` the SDK raises at request time when no credentials are configured, `stop_reason` of `refusal`/`max_tokens`, or no parsed output.
- `_sanitize` doesn't trust the model's output: it drops unknown/duplicate ids, clamps scores to 0–100, filters `matched_skills` to the candidate's actual stored skills, de-duplicates lists, and appends any omitted candidate with score 0 and "Not assessed."

**Response shape** (both engines): `job_description_skills`, `results[]` (`id, candidate_name, original_filename, matched_skills, missing_skills, score, match_percentage`, plus `reasoning` for the LLM engine; for the LLM `score == match_percentage == fit_score`), `excluded_count`, `note`, and `engine` (`"llm"`, `"keyword"`, or `null` when no candidates are reviewed).

**Frontend**: `JobMatch.jsx` has a "Use Claude AI for matching" checkbox (default on) sent as `use_ai` via `matchCandidates(jobDescription, useAi)` in `api.js`. It shows Claude's required skills as chips, an "AI-ranked" hint when `engine === "llm"`, the per-candidate `reasoning`, and "Analyzing…" while the call is in flight.

**Scope / gotchas**:
- Only job matching uses Claude. Upload-time skill suggestions and the QA/QM summary are still rule-based (`skills_extractor.py`).
- If a search unexpectedly shows the fallback note, the backend most likely has a stale or missing key — check the uvicorn log for the `Falling back to keyword matching:` warning. On Windows, killing a `--reload` uvicorn parent can leave its spawned worker process still bound to port 8000 and serving old code/env; check `netstat -ano | findstr :8000` and kill leftover `python.exe` processes before restarting.

### API surface (`backend/app/main.py`)

CRUD (`GET/POST /api/cvs`, `PUT/DELETE /api/cvs/{id}`) plus skill/matching endpoints: `GET /api/cvs/{id}/skills/suggestions` (re-runs extraction against the stored file), `PUT /api/cvs/{id}/skills` (persists the user-reviewed list), `POST /api/match` (body `{job_description, use_ai}`; ranks all reviewed CVs via Claude or the keyword matcher — see above), and `GET /api/cvs/{id}/file` (serves the original file for download/preview). File validation (extension + content-type + 10 MB cap) happens in `main.py`, not `storage.py`.

### Frontend structure

- `App.jsx` owns all top-level state (CV list, search filter, which modal is open) and passes callbacks down; there's no router or global store.
- Upload → `handleUploaded` immediately opens `SkillsReviewModal` with the server's `suggested_skills` so the user reviews before skills are persisted.
- `JobMatch.jsx` is self-contained (its own form/result/AI-toggle state) and calls `POST /api/match` via `matchCandidates`.
- `api.js` is the only place `fetch` is called; every function funnels through the shared `handle()` helper for error unwrapping (reads `detail` from JSON error bodies).
