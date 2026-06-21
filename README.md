# AI Mock Interview Platform

Upload a résumé → get interview questions tailored to a target role → answer them → get structured, scored feedback. Built as a structured agent, not a chat wrapper: every LLM call is forced to return validated JSON matching a strict schema, never freeform prose.

## Architecture

```
PDF résumé
  → pdfplumber extracts + sanitizes raw text
  → LLM call #1: structure into ResumeProfile (skills, roles, years exp)
  ↓
Target role (user input)
  → LLM call #2: generate QuestionSet (behavioral + technical, tailored)
  ↓
User answers each question (typed, one at a time)
  ↓
  → LLM call #3 (batched): score all answers → InterviewSummary
    (per-question scores + overall competency breakdown)
```

Every stage is defined as a Pydantic schema in `backend/app/schemas.py` — that's the contract the LLM is forced into via `response_mime_type="application/json"`, with a one-shot repair retry if it ever returns malformed JSON.

## Project structure

```
backend/
  app/
    main.py              FastAPI app, 3 endpoints
    schemas.py           Pydantic models — the structured contracts
    llm_client.py         Gemini wrapper, forces JSON output + repair retry
    resume_parser.py      PDF -> sanitized text -> ResumeProfile
    question_generator.py ResumeProfile + role -> QuestionSet
    feedback_engine.py    Answers -> scored InterviewSummary
  requirements.txt
  .env.example

frontend/
  src/
    App.jsx              State machine: upload -> role -> interview -> summary
    index.css            "Exam room" design: serif questions, mono scores
    main.jsx
  index.html
  vite.config.js
  package.json
```

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and add your Gemini API key — get one free at https://aistudio.google.com/apikey
export GEMINI_API_KEY=your_key_here   # or use a tool like python-dotenv / direnv

uvicorn app.main:app --reload --port 8000
```

Backend will run at `http://localhost:8000`. Check `http://localhost:8000/api/health` to confirm it's up. Interactive API docs are auto-generated at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at `http://localhost:5173` and call the backend at `http://localhost:8000` by default. To point at a different backend URL, set `VITE_API_BASE` in a `.env` file in `frontend/`.

## API endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/parse-resume` | multipart PDF file | `ResumeProfile` |
| POST | `/api/generate-questions` | `{ resume_profile, target_role, num_questions }` | `QuestionSet` |
| POST | `/api/submit-answers` | `{ target_role, answers[] }` | `InterviewSummary` |

The frontend holds all state client-side (resume profile, questions, answers) and passes it back on each call — there's no server-side session/database yet. This keeps the backend stateless and easy to reason about while you validate the core flow.

## Known limitations / what to harden before shipping

- **No persistence.** Refreshing the page loses everything. Add a Postgres table (or even SQLite to start) keyed by a session ID if you want users to resume or review past interviews.
- **No auth.** Anyone can hit the API. Fine for a local prototype, not for a public deploy.
- **CORS is wide open** (`allow_origins=["*"]`) — tighten to your actual frontend origin before deploying.
- **Scanned/image-only PDFs will fail** — `pdfplumber` only extracts real text layers. Add OCR (e.g. `pytesseract`) if you need to support scanned résumés.
- **Single LLM provider.** `llm_client.py` is the only place that talks to Gemini — swapping providers (e.g. Claude, OpenAI) means only touching that one file, by design.
- **Rate limiting / cost control** isn't implemented. Each full interview run is 3 LLM calls (1 parse + 1 generate + 1 score); add request throttling before opening this up publicly.

## Suggested next steps

1. Get this running locally end-to-end with a real résumé.
2. Add voice input (Web Speech API for STT) as a v2 — the interview loop in `App.jsx` is already isolated enough that swapping the `<textarea>` for a mic capture component shouldn't touch the rest of the flow.
3. Add a results history page once you add persistence.
