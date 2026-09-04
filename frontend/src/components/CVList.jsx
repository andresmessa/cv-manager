import { Fragment } from "react";
import { fileUrl } from "../api.js";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString();
}

const MAX_VISIBLE_SKILLS = 6;

export default function CVList({ cvs, loading, error, onEdit, onDelete, onReviewSkills, isFiltered = false }) {
  if (loading) return <p>Loading CVs…</p>;
  if (error) return <p className="error">{error}</p>;
  if (cvs.length === 0) {
    return <p className="empty">{isFiltered ? "No CVs match your search." : "No CVs uploaded yet."}</p>;
  }

  return (
    <div className="table-scroll">
      <table className="cv-table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>File</th>
            <th>Size</th>
            <th>Uploaded</th>
            <th>QE Skills</th>
            <th aria-label="Actions"></th>
          </tr>
        </thead>
        <tbody>
          {cvs.map((cv) => (
            <Fragment key={cv.id}>
              <tr className="cv-row">
                <td>{cv.candidate_name}</td>
                <td>
                  <a href={fileUrl(cv.id)} target="_blank" rel="noreferrer">
                    {cv.original_filename}
                  </a>
                </td>
                <td>{formatSize(cv.size)}</td>
                <td>{formatDate(cv.uploaded_at)}</td>
                <td>
                  {cv.skills && cv.skills.length > 0 ? (
                    <div className="skill-chips">
                      {cv.skills.slice(0, MAX_VISIBLE_SKILLS).map((skill) => (
                        <span className="skill-chip" key={skill}>
                          {skill}
                        </span>
                      ))}
                      {cv.skills.length > MAX_VISIBLE_SKILLS && (
                        <span className="hint">+{cv.skills.length - MAX_VISIBLE_SKILLS} more</span>
                      )}
                    </div>
                  ) : (
                    <span className="hint">Not reviewed</span>
                  )}
                </td>
                <td>
                  <div className="actions">
                    <button className="secondary" onClick={() => onReviewSkills(cv)}>
                      Review Skills
                    </button>
                    <button className="secondary" onClick={() => onEdit(cv)}>
                      Edit
                    </button>
                    <button className="danger" onClick={() => onDelete(cv)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
              <tr className="cv-summary-row">
                <td colSpan={6}>
                  <span className="summary-label">QA/QM Summary:</span>{" "}
                  {cv.summary ? cv.summary : <span className="hint">No summary available yet.</span>}
                </td>
              </tr>
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
