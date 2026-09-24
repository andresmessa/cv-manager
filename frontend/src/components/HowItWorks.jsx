import { useState } from "react";

// Section heading with a "How it works" toggle that reveals an explanation panel.
export default function HowItWorks({ title, panelId, children }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="list-header">
        <h2>{title}</h2>
        <button
          type="button"
          className="secondary"
          onClick={() => setOpen((prev) => !prev)}
          aria-expanded={open}
          aria-controls={panelId}
        >
          {open ? "Hide explanation" : "How it works"}
        </button>
      </div>
      {open && (
        <div id={panelId} className="help-panel">
          {children}
        </div>
      )}
    </>
  );
}
