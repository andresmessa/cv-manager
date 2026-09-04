import { useState } from "react";
import { saveSkills } from "../api.js";

export default function SkillsReviewModal({ cv, initialSkills, note, onClose, onSaved }) {
  const [skills, setSkills] = useState(initialSkills);
  const [newSkill, setNewSkill] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function handleEdit(index, value) {
    setSkills((prev) => prev.map((s, i) => (i === index ? value : s)));
  }

  function handleDelete(index) {
    setSkills((prev) => prev.filter((_, i) => i !== index));
  }

  function handleAdd() {
    const trimmed = newSkill.trim();
    if (!trimmed) return;
    setSkills((prev) => [...prev, trimmed]);
    setNewSkill("");
  }

  async function handleSave() {
    setError("");
    setSaving(true);
    try {
      const cleaned = skills.map((s) => s.trim()).filter(Boolean);
      const updated = await saveSkills(cv.id, cleaned);
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="card modal skills-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Review Quality Engineering Skills</h2>
        <p className="hint">
          Detected from <strong>{cv.original_filename}</strong> for {cv.candidate_name}. Edit or delete any skill,
          add ones we missed, then save.
        </p>
        {note && <p className="notice">{note}</p>}

        {skills.length === 0 ? (
          <p className="empty">No skills yet — add some below.</p>
        ) : (
          <ul className="skills-list">
            {skills.map((skill, index) => (
              <li key={index} className="skills-list-row">
                <input
                  type="text"
                  value={skill}
                  onChange={(e) => handleEdit(index, e.target.value)}
                  aria-label={`Skill ${index + 1}`}
                />
                <button
                  type="button"
                  className="danger"
                  onClick={() => handleDelete(index)}
                  aria-label={`Delete ${skill}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="field add-skill-row">
          <label htmlFor="new-skill">Add a skill</label>
          <div className="add-skill-input">
            <input
              id="new-skill"
              type="text"
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAdd();
                }
              }}
              placeholder="e.g. Six Sigma"
            />
            <button type="button" className="secondary" onClick={handleAdd}>
              Add
            </button>
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save skills"}
          </button>
        </div>
      </div>
    </div>
  );
}
