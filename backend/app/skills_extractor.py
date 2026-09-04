import io
import re

from docx import Document
from pypdf import PdfReader

# Canonical manufacturing / Quality Engineer skill -> alias phrases to search for.
# Multi-word aliases are matched as substrings; single acronyms are matched on word
# boundaries to reduce false positives.
SKILL_TAXONOMY: dict[str, list[str]] = {
    "Six Sigma": ["six sigma"],
    "Six Sigma Green Belt": ["green belt"],
    "Six Sigma Black Belt": ["black belt"],
    "Lean Manufacturing": ["lean manufacturing", "lean production", "lean methodology", "lean tools"],
    "Kaizen": [r"\bkaizen\b"],
    "5S Methodology": [r"\b5s\b"],
    "Statistical Process Control (SPC)": [r"\bspc\b", "statistical process control"],
    "Process Capability Analysis (Cpk/Ppk)": [r"\bcpk\b", r"\bppk\b", "process capability"],
    "Measurement System Analysis (MSA)": [r"\bmsa\b", "measurement system analysis"],
    "Design of Experiments (DOE)": [r"\bdoe\b", "design of experiments"],
    "Failure Mode and Effects Analysis (FMEA)": [r"\bfmea\b", "failure mode"],
    "Root Cause Analysis": ["root cause analysis", r"\brca\b"],
    "8D Problem Solving": [r"\b8d\b", "eight disciplines"],
    "Corrective and Preventive Action (CAPA)": [r"\bcapa\b", "corrective and preventive action"],
    "Advanced Product Quality Planning (APQP)": [r"\bapqp\b"],
    "Production Part Approval Process (PPAP)": [r"\bppap\b"],
    "Control Plan Development": ["control plan"],
    "Quality Management System (QMS)": [r"\bqms\b", "quality management system"],
    "ISO 9001": ["iso 9001", "iso9001"],
    "ISO 13485": ["iso 13485", "iso13485"],
    "IATF 16949": ["iatf 16949", "ts 16949", "iatf16949"],
    "ISO 14001": ["iso 14001", "iso14001"],
    "ISO/IEC 17025": ["iso 17025", "iso/iec 17025"],
    "AS9100": ["as9100", "as 9100"],
    "Good Manufacturing Practice (GMP)": [r"\bgmp\b", "good manufacturing practice"],
    "AQL Sampling": [r"\baql\b", "acceptable quality limit"],
    "Incoming Quality Inspection": ["incoming quality", "incoming inspection"],
    "In-Process Quality Inspection": ["in-process inspection", "in process inspection"],
    "Final/Outgoing Quality Inspection": ["final inspection", "outgoing inspection", "pre-shipment inspection"],
    "Supplier Quality Management": ["supplier quality"],
    "Supplier/Vendor Audits": ["supplier audit", "vendor audit"],
    "Internal Quality Audits": ["internal audit", "quality audit"],
    "Factory/Social Compliance Audits": ["social compliance", "factory audit"],
    "Geometric Dimensioning and Tolerancing (GD&T)": [r"\bgd&t\b", "geometric dimensioning"],
    "Blueprint / Engineering Drawing Reading": ["blueprint reading", "engineering drawing"],
    "Coordinate Measuring Machine (CMM)": [r"\bcmm\b", "coordinate measuring machine"],
    "Calibration Management": ["calibration"],
    "Metrology": [r"\bmetrology\b"],
    "Non-Destructive Testing (NDT)": [r"\bndt\b", "non-destructive testing", "nondestructive testing"],
    "Dimensional Inspection": ["dimensional inspection"],
    "Non-Conformance Management": ["non-conformance", "nonconformance", "nc report"],
    "Deviation / Waiver Management": ["deviation report", "waiver request"],
    "Cost of Quality Analysis": ["cost of quality"],
    "Pareto Analysis": ["pareto"],
    "Fishbone / Ishikawa Diagram": ["fishbone", "ishikawa"],
    "Control Charts": ["control chart"],
    "Poka-Yoke (Error Proofing)": ["poka-yoke", "poka yoke", "error proofing"],
    "Value Stream Mapping": ["value stream mapping"],
    "RoHS Compliance": [r"\brohs\b"],
    "REACH Compliance": [r"\breach compliance\b", "reach regulation"],
    "CE Marking Compliance": ["ce marking", "ce mark"],
    "FDA Regulatory Compliance": [r"\bfda\b"],
    "Warranty / Field Failure Analysis": ["field failure", "warranty analysis"],
    "Reliability Testing": ["reliability testing"],
    "Environmental Stress Testing": ["environmental stress", "hass", "halt testing"],
    "Welding Inspection": ["welding inspection", "weld inspection"],
    "Electrical Safety Testing": ["electrical safety", "hipot test"],
    "Material Testing": ["material testing", "material analysis"],
    "Minitab": [r"\bminitab\b"],
    "SAP Quality Management (QM) Module": ["sap qm", "sap quality management"],
    "Certified Quality Engineer (CQE)": [r"\bcqe\b", "certified quality engineer"],
    "Certified Six Sigma Black Belt (CSSBB)": [r"\bcssbb\b"],
    "Manufacturing Process Improvement": ["process improvement"],
    "Process Validation": ["process validation"],
    "Equipment Qualification (IQ/OQ/PQ)": [r"\biq/oq/pq\b", "installation qualification", "operational qualification"],
    "Document Control": ["document control"],
    "Engineering Change Management": ["engineering change", "change request"],
    "Supplier Corrective Action Request (SCAR)": [r"\bscar\b", "supplier corrective action"],
    "Root Cause & Corrective Action (RCCA)": [r"\brcca\b"],
}


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> tuple[str | None, str | None]:
    """Returns (extracted_text, note). extracted_text is None when unsupported."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                return None, "No selectable text found in this PDF (it may be a scanned image)."
            return text, None
        except Exception:
            return None, "Could not read text from this PDF."

    if ext == "docx":
        try:
            document = Document(io.BytesIO(file_bytes))
            parts = [p.text for p in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)
            text = "\n".join(parts)
            if not text.strip():
                return None, "No text found in this document."
            return text, None
        except Exception:
            return None, "Could not read text from this document."

    if ext == "doc":
        return None, "Automatic skill extraction isn't supported for legacy .doc files. Add skills manually below."

    return None, "Automatic skill extraction isn't supported for this file type."


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for canonical, aliases in SKILL_TAXONOMY.items():
        for alias in aliases:
            pattern = alias if alias.startswith(r"\b") else re.escape(alias)
            if re.search(pattern, lowered):
                found.append(canonical)
                break
    return found
