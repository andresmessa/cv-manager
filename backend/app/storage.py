import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
METADATA_FILE = DATA_DIR / "metadata.json"

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_lock = threading.Lock()


def _ensure_storage() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not METADATA_FILE.exists():
        METADATA_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict]:
    _ensure_storage()
    with METADATA_FILE.open("r", encoding="utf-8") as f:
        records = json.load(f)
    for record in records:
        record.setdefault("skills", [])
        record.setdefault("summary", "")
    return records


def _write_all(records: list[dict]) -> None:
    with METADATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def list_cvs() -> list[dict]:
    with _lock:
        records = _read_all()
    return sorted(records, key=lambda r: r["candidate_name"].lower())


def get_cv(cv_id: str) -> dict | None:
    with _lock:
        records = _read_all()
    return next((r for r in records if r["id"] == cv_id), None)


def create_cv(
    original_filename: str,
    content_type: str,
    size: int,
    candidate_name: str,
    file_bytes: bytes,
    summary: str = "",
) -> dict:
    ext = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid.uuid4()}{ext}"
    (UPLOADS_DIR / stored_filename).write_bytes(file_bytes)

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "candidate_name": candidate_name or Path(original_filename).stem,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "content_type": content_type,
        "size": size,
        "skills": [],
        "summary": summary,
        "uploaded_at": now,
        "updated_at": now,
    }

    with _lock:
        records = _read_all()
        records.append(record)
        _write_all(records)

    return record


def update_cv(
    cv_id: str,
    candidate_name: str | None,
    new_original_filename: str | None,
    new_content_type: str | None,
    new_size: int | None,
    new_file_bytes: bytes | None,
    new_summary: str | None = None,
) -> dict | None:
    with _lock:
        records = _read_all()
        record = next((r for r in records if r["id"] == cv_id), None)
        if record is None:
            return None

        if candidate_name is not None:
            record["candidate_name"] = candidate_name

        if new_file_bytes is not None:
            old_path = UPLOADS_DIR / record["stored_filename"]
            ext = Path(new_original_filename).suffix.lower()
            stored_filename = f"{uuid.uuid4()}{ext}"
            (UPLOADS_DIR / stored_filename).write_bytes(new_file_bytes)
            if old_path.exists():
                old_path.unlink()

            record["stored_filename"] = stored_filename
            record["original_filename"] = new_original_filename
            record["content_type"] = new_content_type
            record["size"] = new_size
            record["skills"] = []
            record["summary"] = new_summary or ""

        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_all(records)

    return record


def update_skills(cv_id: str, skills: list[str]) -> dict | None:
    with _lock:
        records = _read_all()
        record = next((r for r in records if r["id"] == cv_id), None)
        if record is None:
            return None

        record["skills"] = skills
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_all(records)

    return record


def delete_cv(cv_id: str) -> bool:
    with _lock:
        records = _read_all()
        record = next((r for r in records if r["id"] == cv_id), None)
        if record is None:
            return False

        records = [r for r in records if r["id"] != cv_id]
        _write_all(records)

        file_path = UPLOADS_DIR / record["stored_filename"]
        if file_path.exists():
            file_path.unlink()

    return True
