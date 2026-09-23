import { useRef, useState } from "react";
import { updateCV } from "../api.js";

export default function EditCVModal({ cv, onClose, onUpdated }) {
  const [candidateName, setCandidateName] = useState(cv.candidate_name);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      onUpdated(await updateCV(cv.id, { candidateName: candidateName.trim(), file }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="card modal" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>Edit CV</h2>
        <div className="field">
          <label htmlFor="edit-candidate-name">Candidate name</label>
          <input
            id="edit-candidate-name"
            type="text"
            value={candidateName}
            onChange={(e) => setCandidateName(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="edit-cv-file">Replace file (optional)</label>
          <input
            id="edit-cv-file"
            type="file"
            ref={fileInputRef}
            accept=".pdf,.doc,.docx"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <p className="hint">Current file: {cv.original_filename}</p>
        </div>
        {error && <p className="error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
