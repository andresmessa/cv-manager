import { useCallback, useEffect, useMemo, useState } from "react";
import UploadForm from "./components/UploadForm.jsx";
import CVList from "./components/CVList.jsx";
import EditCVModal from "./components/EditCVModal.jsx";
import SkillsReviewModal from "./components/SkillsReviewModal.jsx";
import JobMatch from "./components/JobMatch.jsx";
import { listCVs, deleteCV, getSkillSuggestions } from "./api.js";

// Saved skills first, then any suggestions not already present.
function mergeSkills(saved, suggested) {
  return [...saved, ...suggested.filter((skill) => !saved.includes(skill))];
}

export default function App() {
  const [cvs, setCvs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingCv, setEditingCv] = useState(null);
  const [search, setSearch] = useState("");
  const [skillsReview, setSkillsReview] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setCvs(await listCVs());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filteredCvs = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return cvs;
    return cvs.filter(
      (cv) =>
        cv.candidate_name.toLowerCase().includes(term) ||
        cv.original_filename.toLowerCase().includes(term),
    );
  }, [cvs, search]);

  async function handleDelete(cv) {
    if (!window.confirm(`Delete CV for "${cv.candidate_name}"? This cannot be undone.`)) return;
    try {
      await deleteCV(cv.id);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUploaded(uploaded) {
    await refresh();
    setSkillsReview({
      cv: uploaded,
      initialSkills: uploaded.suggested_skills ?? [],
      note: uploaded.extraction_note ?? null,
    });
  }

  async function handleEdited(updated) {
    setEditingCv(null);
    await refresh();
    // A replaced file comes back with suggestions (like an upload): review them straight
    // away, together with the hand-added skills the server kept on the record.
    if (updated.suggested_skills) {
      setSkillsReview({
        cv: updated,
        initialSkills: mergeSkills(updated.skills, updated.suggested_skills),
        note: updated.extraction_note ?? null,
      });
    }
  }

  async function handleReviewSkills(cv) {
    setError("");
    try {
      const { suggested_skills, extraction_note } = await getSkillSuggestions(cv.id);
      setSkillsReview({ cv, initialSkills: mergeSkills(cv.skills, suggested_skills), note: extraction_note });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>CV Manager</h1>
        <p className="subtitle">Upload, review, update, and delete candidate CVs.</p>
      </header>

      <UploadForm onUploaded={handleUploaded} />

      <section className="card">
        <div className="list-header">
          <h2>Uploaded CVs</h2>
          <input
            type="text"
            className="search-input"
            placeholder="Search by candidate or filename…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search CVs"
          />
        </div>
        <CVList
          cvs={filteredCvs}
          loading={loading}
          error={error}
          onEdit={setEditingCv}
          onDelete={handleDelete}
          onReviewSkills={handleReviewSkills}
          isFiltered={search.trim().length > 0}
        />
      </section>

      <JobMatch />

      {editingCv && (
        <EditCVModal
          cv={editingCv}
          onClose={() => setEditingCv(null)}
          onUpdated={handleEdited}
        />
      )}

      {skillsReview && (
        <SkillsReviewModal
          cv={skillsReview.cv}
          initialSkills={skillsReview.initialSkills}
          note={skillsReview.note}
          onClose={() => setSkillsReview(null)}
          onSaved={async () => {
            setSkillsReview(null);
            await refresh();
          }}
        />
      )}
    </div>
  );
}
