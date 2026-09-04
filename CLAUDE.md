# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

CV Manager: a small web app for uploading, listing, updating, and deleting candidate CVs (PDF/DOC/DOCX), extracting quality-engineering skills from them, and matching candidates against a pasted job description.

- **Backend**: Python + FastAPI, single-process, no database — metadata lives in a JSON file and files on local disk.
- **Frontend**: React + Vite, no state management library — all state lives in `App.jsx` and is passed down as props.

## Commands

### Backend (from `backend/`)

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

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

- `SKILL_TAXONOMY` is a hand-maintained dict mapping canonical quality-engineering skill names (Six Sigma, ISO 9001, CMM, GD&T, etc.) to lists of alias patterns. Aliases starting with `\b` are treated as regexes matched against lowercased text; everything else is escaped and matched as a literal substring. Extending recognized skills means adding entries here — extraction and job-description parsing both call `extract_skills()`, so the taxonomy is the single source of truth for both directions of matching.
- Text is pulled from PDFs via `pypdf` and from `.docx` via `python-docx` (paragraphs + table cells); legacy `.doc` and scanned/text-less PDFs are explicitly unsupported and surface a user-facing note instead of failing silently.
- Skill suggestions from upload/extraction are never auto-saved — they only become part of a CV's `skills` once the user confirms them through the skills-review flow (`PUT /api/cvs/{id}/skills`). Candidate matching (`POST /api/match`) only considers CVs whose `skills` array is non-empty ("reviewed"); unreviewed CVs are silently excluded and counted in `excluded_count`.

### API surface (`backend/app/main.py`)

CRUD (`GET/POST /api/cvs`, `PUT/DELETE /api/cvs/{id}`) plus skill/matching endpoints: `GET /api/cvs/{id}/skills/suggestions` (re-runs extraction against the stored file), `PUT /api/cvs/{id}/skills` (persists the user-reviewed list), `POST /api/match` (scores all reviewed CVs against skills detected in a pasted job description, sorted by match count then name), and `GET /api/cvs/{id}/file` (serves the original file for download/preview). File validation (extension + content-type + 10 MB cap) happens in `main.py`, not `storage.py`.

### Frontend structure

- `App.jsx` owns all top-level state (CV list, search filter, which modal is open) and passes callbacks down; there's no router or global store.
- Upload → `handleUploaded` immediately opens `SkillsReviewModal` with the server's `suggested_skills` so the user reviews before skills are persisted.
- `JobMatch.jsx` is self-contained (its own form/result state) and calls `POST /api/match` directly.
- `api.js` is the only place `fetch` is called; every function funnels through the shared `handle()` helper for error unwrapping (reads `detail` from JSON error bodies).
