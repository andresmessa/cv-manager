# CV Manager

A small web app for managing candidate CVs (PDF/DOC/DOCX) for quality-engineering roles:

- **Upload, list, update and delete CVs.**
- **Skills review** — quality-engineering skills are suggested from each CV's text; the user confirms them before they're saved.
- **Find best-fit candidates** — paste a job description (free text) and get a ranked list of candidates based on their reviewed skills. Ranking uses keyword matching by default (no API call); switch on the AI toggle to have **Claude** (Anthropic API) rank candidates instead.

- **Backend**: Python + FastAPI. Stores files on local disk (`backend/data/uploads/`) and metadata in a JSON file (`backend/data/metadata.json`).
- **Frontend**: React + Vite.

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm — [download here](https://nodejs.org/)
- An Anthropic API key for AI matching (optional — without it, matching falls back to keywords)

## 1. Set the Anthropic API key

Create a key at [console.anthropic.com](https://console.anthropic.com/) and store it as a **Windows user environment variable** named `ANTHROPIC_API_KEY` (System Properties → Environment Variables). Open a **new** terminal afterwards — existing terminals don't see the change.

Never put the real key in a tracked file (e.g. `StartStop.txt`) or commit it.

## 2. Run the backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## 3. Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. It proxies `/api` requests to the backend on port 8000, so run both servers at the same time.

## Finding best-fit candidates

Only candidates whose skills have been reviewed are considered.

1. Paste a job description into **Find Best-Fit Candidates**.
2. Choose the mode with the **Use Claude AI for matching** checkbox:
   - **Off (default)** — keyword matching against a built-in skill list. Instant, no API call, but only exact skill matches count.
   - **On** — clicking **Find Matches** first shows a **token estimate**: exact input tokens, an estimated output-token range, and the approximate cost. Click **Run AI search** to proceed or **Cancel**. Claude (`claude-sonnet-5`) then works out the skills the job requires and ranks every candidate 0–100 with a short explanation, giving partial credit for related skills. The actual tokens used and cost are shown with the results.
3. If the AI call fails (missing/invalid key, network, etc.), the app automatically shows keyword results with the note "AI matching unavailable".

Only each candidate's id and reviewed skills are sent to Claude — no names, filenames or CV contents.

## API endpoints

| Method | Path                               | Description |
| ------ | ---------------------------------- | ----------- |
| GET    | `/api/cvs`                         | List all uploaded CVs |
| POST   | `/api/cvs`                         | Upload a new CV (`file`, optional `candidate_name`); returns suggested skills |
| PUT    | `/api/cvs/{id}`                    | Update a CV's candidate name and/or file |
| DELETE | `/api/cvs/{id}`                    | Delete a CV |
| GET    | `/api/cvs/{id}/file`               | Download/view the stored file |
| GET    | `/api/cvs/{id}/skills/suggestions` | Re-extract suggested skills from the stored file |
| PUT    | `/api/cvs/{id}/skills`             | Save the user-reviewed skills list |
| POST   | `/api/match/estimate`              | Token/cost preview for an AI match (`{job_description}`) |
| POST   | `/api/match`                       | Rank reviewed candidates (`{job_description, use_ai}`) |

Only `.pdf`, `.doc`, and `.docx` files up to 10 MB are accepted.

## Project structure

```
backend/
  app/
    main.py              # FastAPI routes, keyword matcher, AI/fallback orchestration
    llm_matcher.py       # Claude ranking + token estimate
    skills_extractor.py  # Text extraction, skill taxonomy, QA/QM summary
    storage.py           # File + JSON metadata persistence
  data/
    uploads/             # Uploaded CV files
    metadata.json        # CV metadata
  requirements.txt
frontend/
  src/
    components/          # UploadForm, CVList, EditCVModal, SkillsReviewModal, JobMatch
    api.js               # Backend API client
    App.jsx
  package.json
  vite.config.js
```

See `CLAUDE.md` for architecture details and development notes.
