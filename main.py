"""
FastAPI application: ties together resume parsing, question generation, and feedback.

Endpoints:
  POST /api/parse-resume        -> ResumeProfile
  POST /api/generate-questions  -> QuestionSet
  POST /api/submit-answers      -> InterviewSummary

State is NOT persisted server-side beyond a single request — the frontend holds
the resume profile, question set, and answers in memory and passes them back on
each call. Simple, stateless, easy to reason about. Add a DB later if you need
multi-session history.
"""

import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    ResumeProfile,
    QuestionSet,
    InterviewSummary,
    GenerateQuestionsRequest,
    SubmitAnswersRequest,
)
from app.resume_parser import parse_resume_to_profile
from app.question_generator import generate_questions
from app.feedback_engine import generate_feedback

app = FastAPI(title="AI Mock Interview Platform")

# In production, set ALLOWED_ORIGINS to your Netlify URL, e.g.:
# ALLOWED_ORIGINS=https://your-site.netlify.app
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = (
    [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    if allowed_origins_env
    else ["http://localhost:5173"]  # local dev default
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/parse-resume", response_model=ResumeProfile)
async def parse_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5MB).")

    try:
        profile = await parse_resume_to_profile(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")

    return profile


@app.post("/api/generate-questions", response_model=QuestionSet)
async def generate_questions_endpoint(req: GenerateQuestionsRequest):
    try:
        question_set = await generate_questions(
            profile=req.resume_profile,
            target_role=req.target_role,
            num_questions=req.num_questions,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {e}")

    return question_set


@app.post("/api/submit-answers", response_model=InterviewSummary)
async def submit_answers_endpoint(req: SubmitAnswersRequest):
    try:
        summary = await generate_feedback(target_role=req.target_role, answers=req.answers)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate feedback: {e}")

    return summary
