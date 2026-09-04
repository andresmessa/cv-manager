# CV Manager

A small web app with four services: upload, list, update, and delete candidate CVs (PDF/DOC/DOCX).

- **Backend**: Python + FastAPI. Stores files on local disk (`backend/data/uploads/`) and metadata in a JSON file (`backend/data/metadata.json`).
- **Frontend**: React + Vite.

## Prerequisites

- Python 3.10+ (already installed on this machine)
- Node.js 18+ and npm — [download here](https://nodejs.org/) (not yet installed on this machine)

## 1. Run the backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## 2. Run the frontend

In a second terminal, once Node.js is installed:

```powershell
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`. It proxies `/api` requests to the backend on port 8000, so run both servers at the same time.

## API endpoints

| Method | Path                  | Description                                  |
| ------ | --------------------- | --------------------------------------------- |
| GET    | `/api/cvs`             | List all uploaded CVs                        |
| POST   | `/api/cvs`             | Upload a new CV (`file`, optional `candidate_name`) |
| PUT    | `/api/cvs/{id}`        | Update a CV's candidate name and/or file      |
| DELETE | `/api/cvs/{id}`        | Delete a CV                                   |
| GET    | `/api/cvs/{id}/file`   | Download/view the stored file                 |

Only `.pdf`, `.doc`, and `.docx` files up to 10 MB are accepted.

## Project structure

```
backend/
  app/
    main.py        # FastAPI routes
    storage.py      # File + JSON metadata persistence
  data/
    uploads/         # Uploaded CV files
    metadata.json    # CV metadata
  requirements.txt
frontend/
  src/
    components/      # UploadForm, CVList, EditCVModal
    api.js           # Backend API client
    App.jsx
  package.json
  vite.config.js
```
