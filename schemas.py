"""
Structured data contracts for the interview pipeline.

Design principle: every LLM call is forced to return data matching one of these
schemas. No freeform prose passed between stages — only validated, typed JSON.
This is what separates an "agent" from a chat wrapper.
"""

from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


# ---------------------------------------------------------------------------
# Stage 1: Resume parsing output
# ---------------------------------------------------------------------------

class ResumeProfile(BaseModel):
    """Extracted, structured representation of a raw resume."""
    candidate_name: str | None = None
    years_experience: float | None = Field(
        default=None, description="Estimated total years of professional experience"
    )
    current_or_last_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    past_roles: list[str] = Field(
        default_factory=list, description="e.g. 'Backend Engineer at Acme Corp (2021-2023)'"
    )
    education: list[str] = Field(default_factory=list)
    raw_text_excerpt: str = Field(
        default="", description="Truncated raw text kept for LLM grounding, not display"
    )


# ---------------------------------------------------------------------------
# Stage 2: Question generation output
# ---------------------------------------------------------------------------

class QuestionType(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"


class InterviewQuestion(BaseModel):
    id: str
    type: QuestionType
    question: str
    focus_area: str = Field(description="e.g. 'System Design', 'Conflict Resolution', 'Python'")
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    rationale: str = Field(
        description="Why this question was chosen for this candidate/role (internal, can show as a tooltip)"
    )


class QuestionSet(BaseModel):
    target_role: str
    questions: list[InterviewQuestion]


# ---------------------------------------------------------------------------
# Stage 3: Answer submission (input from user)
# ---------------------------------------------------------------------------

class AnswerSubmission(BaseModel):
    question_id: str
    question_text: str
    question_type: QuestionType
    focus_area: str
    answer_text: str


# ---------------------------------------------------------------------------
# Stage 4: Feedback / scoring output
# ---------------------------------------------------------------------------

class AnswerFeedback(BaseModel):
    question_id: str
    score: int = Field(ge=1, le=10, description="Overall quality score for this answer")
    clarity_score: int = Field(ge=1, le=10)
    relevance_score: int = Field(ge=1, le=10)
    depth_score: int = Field(ge=1, le=10, description="Technical/behavioral depth and specificity")
    strengths: list[str] = Field(default_factory=list, max_length=4)
    gaps: list[str] = Field(default_factory=list, max_length=4)
    improved_answer_tip: str = Field(
        description="One concrete, actionable tip — not a full rewritten answer"
    )


class InterviewSummary(BaseModel):
    target_role: str
    overall_score: float = Field(ge=1, le=10)
    competency_breakdown: dict[str, float] = Field(
        default_factory=dict, description="focus_area -> average score, for radar chart"
    )
    top_strengths: list[str] = Field(default_factory=list, max_length=5)
    priority_improvements: list[str] = Field(default_factory=list, max_length=5)
    per_question_feedback: list[AnswerFeedback] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API request/response wrappers
# ---------------------------------------------------------------------------

class GenerateQuestionsRequest(BaseModel):
    resume_profile: ResumeProfile
    target_role: str
    num_questions: int = Field(default=6, ge=3, le=12)


class SubmitAnswersRequest(BaseModel):
    target_role: str
    answers: list[AnswerSubmission]
