import { useRef, useState } from "react";
import { uploadCV } from "../api.js";
import HowItWorks from "./HowItWorks.jsx";

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
      <HowItWorks title="Upload CV" panelId="upload-help">
        <p className="help-callout">
          <strong>No AI is used here.</strong> Your CV is processed entirely on this computer by local parsing
          algorithms. Its contents are never sent to Claude or any other external service.
        </p>
        <ol>
          <li>
            <strong>Upload:</strong> PDF, DOCX or DOC files up to 10 MB are stored locally on this machine.
          </li>
          <li>
            <strong>Text extraction:</strong> the text is read from the file with standard document parsers (PDF
            text layer, or Word paragraphs and tables). Scanned/image-only PDFs and legacy .doc files can&apos;t be
            read, so you&apos;ll add skills for those by hand.
          </li>
          <li>
            <strong>Skill detection:</strong> the text is matched against a built-in list of quality-engineering
            skills (e.g. ISO 9001, SPC, FMEA, CMM) using keyword and pattern rules, including common abbreviations
            and alternative spellings.
          </li>
          <li>
            <strong>Your review:</strong> the detected skills open in the Review Skills dialog. Nothing is saved
            until you confirm, and you can edit, remove or add skills.
          </li>
          <li>
            <strong>Summary:</strong> a short QA/QM summary is generated with rules that look for quality job titles
            and years of experience.
          </li>
        </ol>
        <p className="hint">
          AI is only used, and only if you turn it on, in <em>Find Best-Fit Candidates</em>. Even then, only the
          job description and candidates&apos; reviewed skill names are sent, never CV text, names or files.
        </p>
      </HowItWorks>
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
