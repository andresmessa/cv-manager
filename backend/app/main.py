import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import llm_matcher, skills_extractor, storage

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="CV Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class SkillsPayload(BaseModel):
    skills: list[str]


class JobDescriptionPayload(BaseModel):
    job_description: str
    use_ai: bool = True


def _validate_file(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in storage.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word documents (.pdf, .doc, .docx) are allowed.",
        )
    if file.content_type not in storage.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word documents (.pdf, .doc, .docx) are allowed.",
        )


@app.get("/api/cvs")
def list_cvs():
    return storage.list_cvs()


@app.post("/api/cvs", status_code=201)
async def upload_cv(file: UploadFile = File(...), candidate_name: str = Form("")):
    _validate_file(file)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB size limit.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text, note = skills_extractor.extract_text_from_bytes(contents, file.filename)
    suggested_skills = skills_extractor.extract_skills(text) if text else []
    summary = skills_extractor.generate_summary(text, suggested_skills)

    record = storage.create_cv(
        original_filename=file.filename,
        content_type=file.content_type,
        size=len(contents),
        candidate_name=candidate_name.strip(),
        file_bytes=contents,
        summary=summary,
    )

    return {**record, "suggested_skills": suggested_skills, "extraction_note": note}


@app.put("/api/cvs/{cv_id}")
async def update_cv(cv_id: str, candidate_name: str | None = Form(None), file: UploadFile | None = File(None)):
    new_filename = new_content_type = new_bytes = new_summary = None
    new_size = None
    suggested_skills: list[str] = []
    extraction_note = None

    if file is not None and file.filename:
        _validate_file(file)
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File exceeds the 10 MB size limit.")
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        new_filename = file.filename
        new_content_type = file.content_type
        new_size = len(contents)
        new_bytes = contents

        text, extraction_note = skills_extractor.extract_text_from_bytes(contents, file.filename)
        suggested_skills = skills_extractor.extract_skills(text) if text else []
        new_summary = skills_extractor.generate_summary(text, suggested_skills)

    record = storage.update_cv(
        cv_id,
        candidate_name=candidate_name.strip() if candidate_name is not None else None,
        new_original_filename=new_filename,
        new_content_type=new_content_type,
        new_size=new_size,
        new_file_bytes=new_bytes,
        new_summary=new_summary,
        # Skills detected from the old file are dropped; hand-added ones (not in the
        # taxonomy, so never re-detectable) are kept for the review that follows.
        keep_skill=lambda s: s not in skills_extractor.SKILL_TAXONOMY,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    if new_bytes is None:
        return record
    return {**record, "suggested_skills": suggested_skills, "extraction_note": extraction_note}


@app.delete("/api/cvs/{cv_id}", status_code=204)
def delete_cv(cv_id: str):
    if not storage.delete_cv(cv_id):
        raise HTTPException(status_code=404, detail="CV not found.")


@app.get("/api/cvs/{cv_id}/skills/suggestions")
def get_skill_suggestions(cv_id: str):
    record = storage.get_cv(cv_id)
    if record is None:
        raise HTTPException(status_code=404, detail="CV not found.")

    file_path = storage.UPLOADS_DIR / record["stored_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk.")

    file_bytes = file_path.read_bytes()
    text, note = skills_extractor.extract_text_from_bytes(file_bytes, record["original_filename"])
    suggested_skills = skills_extractor.extract_skills(text) if text else []

    return {"suggested_skills": suggested_skills, "extraction_note": note}


@app.put("/api/cvs/{cv_id}/skills")
def save_skills(cv_id: str, payload: SkillsPayload):
    cleaned = []
    for skill in payload.skills:
        trimmed = skill.strip()
        if trimmed and trimmed not in cleaned:
            cleaned.append(trimmed)

    record = storage.update_skills(cv_id, cleaned)
    if record is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    return record


@app.post("/api/match")
def match_candidates(payload: JobDescriptionPayload):
    job_description, reviewed, excluded_count = _prepare_match(payload)

    if not reviewed:
        return {
            "job_description_skills": [],
            "results": [],
            "excluded_count": excluded_count,
            "note": None,
            "engine": None,
        }

    if not payload.use_ai:
        return _keyword_match(job_description, reviewed, excluded_count)

    try:
        analysis, usage = llm_matcher.rank_candidates(job_description, reviewed)
    except llm_matcher.LLMMatchError as e:
        logger.warning("Falling back to keyword matching: %s", e)
        result = _keyword_match(job_description, reviewed, excluded_count)
        fallback_note = "AI matching unavailable — showing keyword-based results."
        result["note"] = f"{fallback_note} {result['note']}" if result["note"] else fallback_note
        return result

    by_id = {r["id"]: r for r in reviewed}
    results = []
    for ranking in analysis.rankings:
        record = by_id[ranking.candidate_id]
        results.append(
            {
                "id": record["id"],
                "candidate_name": record["candidate_name"],
                "original_filename": record["original_filename"],
                "matched_skills": ranking.matched_skills,
                "missing_skills": ranking.missing_skills,
                "score": ranking.fit_score,
                "match_percentage": ranking.fit_score,
                "reasoning": ranking.reasoning,
            }
        )

    results.sort(key=lambda r: (-r["score"], r["candidate_name"].lower()))

    return {
        "job_description_skills": analysis.required_skills,
        "results": results,
        "excluded_count": excluded_count,
        "note": None,
        "engine": "llm",
        "usage": usage,
    }


@app.post("/api/match/estimate")
def estimate_match(payload: JobDescriptionPayload):
    """Previews the token usage of an AI match without running it (count_tokens is free)."""
    job_description, reviewed, _excluded_count = _prepare_match(payload)
    if not reviewed:
        return {"candidate_count": 0, "input_tokens": 0, "note": "No candidates with reviewed skills yet."}
    try:
        return llm_matcher.estimate_tokens(job_description, reviewed)
    except llm_matcher.LLMMatchError as e:
        logger.warning("Token estimate failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Couldn't reach the Claude API to estimate tokens. Running the search will fall back to keyword matching.",
        )


def _prepare_match(payload: JobDescriptionPayload) -> tuple[str, list[dict], int]:
    job_description = payload.job_description.strip()
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    records = storage.list_cvs()
    reviewed = [r for r in records if r["skills"]]
    return job_description, reviewed, len(records) - len(reviewed)


def _keyword_match(job_description: str, reviewed: list[dict], excluded_count: int) -> dict:
    jd_skills = skills_extractor.extract_skills(job_description)

    if not jd_skills:
        return {
            "job_description_skills": [],
            "results": [],
            "excluded_count": excluded_count,
            "note": "No recognized quality engineering skills were found in this job description. "
            "Try including specific tools, certifications, or methodologies (e.g. Six Sigma, ISO 9001, SPC).",
            "engine": "keyword",
        }

    results = []
    for record in reviewed:
        candidate_skills = set(record["skills"])
        matched = [s for s in jd_skills if s in candidate_skills]
        missing = [s for s in jd_skills if s not in candidate_skills]
        results.append(
            {
                "id": record["id"],
                "candidate_name": record["candidate_name"],
                "original_filename": record["original_filename"],
                "matched_skills": matched,
                "missing_skills": missing,
                "score": len(matched),
                "match_percentage": round(len(matched) / len(jd_skills) * 100),
            }
        )

    results.sort(key=lambda r: (-r["score"], r["candidate_name"].lower()))

    return {
        "job_description_skills": jd_skills,
        "results": results,
        "excluded_count": excluded_count,
        "note": None,
        "engine": "keyword",
    }


@app.get("/api/cvs/{cv_id}/file")
def download_cv(cv_id: str):
    record = storage.get_cv(cv_id)
    if record is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    file_path = storage.UPLOADS_DIR / record["stored_filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk.")
    return FileResponse(
        path=file_path,
        media_type=record["content_type"],
        filename=record["original_filename"],
    )
