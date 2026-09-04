import { useRef, useState } from "react";
import { uploadCV } from "../api.js";

export default function UploadForm({ onUploaded }) {
  const [candidateName, setCandidateName] = useState("");
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a PDF or Word document to upload.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const uploaded = await uploadCV(file, candidateName.trim());
      setCandidateName("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      onUploaded(uploaded);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Upload CV</h2>
      <div className="field">
        <label htmlFor="candidate-name">Candidate name (optional)</label>
        <input
          id="candidate-name"
          type="text"
          value={candidateName}
          onChange={(e) => setCandidateName(e.target.value)}
          placeholder="e.g. Jane Doe"
        />
      </div>
      <div className="field">
        <label htmlFor="cv-file">CV file (.pdf, .doc, .docx)</label>
        <input
          id="cv-file"
          type="file"
          ref={fileInputRef}
          accept=".pdf,.doc,.docx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? "Uploading…" : "Upload"}
      </button>
    </form>
  );
}
