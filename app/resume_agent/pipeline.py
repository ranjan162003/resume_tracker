from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docx2pdf import convert

from app.db import JobPosting, get_session
from app.resume_agent.claude_client import build_prompt, call_claude, parse_edits
from app.resume_agent.docx_editor import apply_edits, extract_paragraphs
from app.resume_agent.job_detail import fetch_linkedin_description, fetch_workatastartup_description


@dataclass
class TailorResult:
    docx_path: Path
    pdf_path: Path
    summary: str


def tailor_resume(job: JobPosting, resume_path: str) -> TailorResult:
    if not resume_path:
        raise ValueError("No resume path set -- add one in Settings first.")
    if not Path(resume_path).exists():
        raise ValueError(f"Resume file not found: {resume_path}")

    description = _ensure_description(job)
    paragraphs = extract_paragraphs(resume_path)
    prompt = build_prompt(paragraphs, description)
    raw_output = call_claude(prompt)
    summary, edits = parse_edits(raw_output)

    stem = _slugify(f"{job.id}-{job.company}-{job.title}")[:80]
    docx_path = apply_edits(resume_path, edits, stem)
    pdf_path = to_pdf(docx_path)

    return TailorResult(docx_path=docx_path, pdf_path=pdf_path, summary=summary)


def to_pdf(docx_path: Path) -> Path:
    pdf_path = docx_path.with_suffix(".pdf")
    convert(str(docx_path), str(pdf_path))
    return pdf_path


def _ensure_description(job: JobPosting) -> str:
    if job.description.strip():
        return job.description

    if job.source == "linkedin":
        description = fetch_linkedin_description(job.url)
    elif job.source == "workatastartup":
        description = fetch_workatastartup_description(job.url)
    else:
        return job.description  # empty, and no fetcher available for this source

    if description:
        with get_session() as session:
            db_job = session.get(JobPosting, job.id)
            if db_job is not None:
                db_job.description = description
                session.commit()
        job.description = description
    return description


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
