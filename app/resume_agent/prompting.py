"""Backend-agnostic prompt building and response parsing, shared by whichever
LLM backend is actually used (Claude Code CLI or a local Ollama model).
"""
from __future__ import annotations

import json
import re

from app.resume_agent.docx_editor import Edit, Paragraph

PROMPT_TEMPLATE = """You are tailoring an existing resume to better match a specific job posting.

Rules (follow exactly):
- Only rephrase, reorder, or re-emphasize content that is already present in the resume paragraphs below. Never invent new skills, employers, job titles, dates, or achievements that aren't already there.
- Focus on the objective/summary paragraph and a handful of the most relevant bullet points -- don't rewrite everything.
- Keep each edited paragraph roughly the same length as the original.
- Reply with ONLY a single JSON object, no markdown code fences, no commentary before or after. Shape exactly:
  {{"summary": "one sentence describing what you changed and why", "edits": [{{"index": <int>, "new_text": "<string>"}}, ...]}}
- "index" must be one of the paragraph indices given below. Only include paragraphs you're actually changing.

JOB DESCRIPTION:
{job_description}

RESUME PARAGRAPHS (index: text):
{paragraphs}
"""


def build_prompt(paragraphs: list[Paragraph], job_description: str) -> str:
    paragraph_lines = "\n".join(f"{p['index']}: {p['text']}" for p in paragraphs)
    return PROMPT_TEMPLATE.format(
        job_description=job_description.strip() or "(no description available)",
        paragraphs=paragraph_lines,
    )


def parse_edits(llm_output: str) -> tuple[str, list[Edit]]:
    text = llm_output.strip()
    # Strip a stray markdown fence if the model adds one despite instructions not to.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"The model's response wasn't valid JSON: {llm_output[:300]}") from e

    if not isinstance(data, dict) or "edits" not in data:
        raise ValueError(f"The model's response was missing the expected 'edits' field: {llm_output[:300]}")

    summary = str(data.get("summary", ""))
    edits: list[Edit] = [
        {"index": int(item["index"]), "new_text": str(item["new_text"])} for item in data["edits"]
    ]
    return summary, edits
