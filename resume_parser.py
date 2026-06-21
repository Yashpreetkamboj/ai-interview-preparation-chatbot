"""
Resume parsing: PDF -> sanitized raw text -> structured ResumeProfile.

Two-step process:
  1. pdfplumber extracts raw text (deterministic, no LLM needed)
  2. LLM call structures that raw text into a ResumeProfile (forced JSON schema)
"""

import pdfplumber
import io
import re

from app.schemas import ResumeProfile
from app.llm_client import call_llm_structured


MAX_RAW_CHARS = 8000  # truncate before sending to LLM to control token usage/latency


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract and lightly sanitize raw text from a PDF resume."""
    text_chunks: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)

    raw_text = "\n".join(text_chunks)
    return _sanitize_text(raw_text)


def _sanitize_text(text: str) -> str:
    """Strip control characters, collapse whitespace, remove obvious noise."""
    # Drop non-printable / control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse 3+ newlines into 2, and runs of spaces into 1
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


PROFILE_EXTRACTION_PROMPT = """You are a resume parser. Extract structured information from the
raw resume text below. Be conservative: only include information that is explicitly present or
strongly implied. Do not invent skills, titles, or experience.

Estimate years_experience as a number by reasoning over listed role date ranges. If you cannot
determine it, return null.

RAW RESUME TEXT:
---
{resume_text}
---

Return ONLY valid JSON matching this exact schema, nothing else:
{{
  "candidate_name": string or null,
  "years_experience": number or null,
  "current_or_last_title": string or null,
  "skills": [string],
  "tools_and_technologies": [string],
  "past_roles": [string],
  "education": [string]
}}"""


async def parse_resume_to_profile(file_bytes: bytes) -> ResumeProfile:
    """Full pipeline: PDF bytes -> ResumeProfile."""
    raw_text = extract_text_from_pdf(file_bytes)

    if not raw_text or len(raw_text) < 30:
        raise ValueError(
            "Could not extract readable text from this PDF. It may be a scanned image "
            "without OCR, or corrupted."
        )

    truncated = raw_text[:MAX_RAW_CHARS]
    prompt = PROFILE_EXTRACTION_PROMPT.format(resume_text=truncated)

    structured = await call_llm_structured(prompt)

    profile = ResumeProfile(
        candidate_name=structured.get("candidate_name"),
        years_experience=structured.get("years_experience"),
        current_or_last_title=structured.get("current_or_last_title"),
        skills=structured.get("skills", []) or [],
        tools_and_technologies=structured.get("tools_and_technologies", []) or [],
        past_roles=structured.get("past_roles", []) or [],
        education=structured.get("education", []) or [],
        raw_text_excerpt=truncated[:2000],
    )
    return profile
