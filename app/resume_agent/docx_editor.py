"""In-place DOCX text edits that preserve the original formatting.

python-docx can't safely regenerate a whole document, but it can overwrite
the text of an existing paragraph without touching its style -- a paragraph's
formatting lives on its runs, so as long as we only change a run's `.text`
(rather than deleting/inserting paragraphs), font, size, bold, and bullet
style all survive untouched.
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from docx import Document

from app.config import TAILORED_DIR


class Paragraph(TypedDict):
    index: int
    text: str


class Edit(TypedDict):
    index: int
    new_text: str


def extract_paragraphs(docx_path: str) -> list[Paragraph]:
    document = Document(docx_path)
    return [
        {"index": i, "text": p.text}
        for i, p in enumerate(document.paragraphs)
        if p.text.strip()
    ]


def apply_edits(docx_path: str, edits: list[Edit], output_stem: str) -> Path:
    document = Document(docx_path)
    edits_by_index = {edit["index"]: edit["new_text"] for edit in edits}

    for i, paragraph in enumerate(document.paragraphs):
        if i not in edits_by_index:
            continue
        _set_paragraph_text(paragraph, edits_by_index[i])

    output_path = TAILORED_DIR / f"{output_stem}.docx"
    document.save(output_path)
    return output_path


def _set_paragraph_text(paragraph, new_text: str) -> None:
    if not paragraph.runs:
        paragraph.add_run(new_text)
        return
    paragraph.runs[0].text = new_text
    for run in paragraph.runs[1:]:
        run.text = ""
