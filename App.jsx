import { useState, useCallback } from "react";

/* ============================================================================
   AI Mock Interview Platform — frontend state machine
   Stages: upload -> role -> questions(loading) -> interview -> feedback(loading) -> summary
   ============================================================================ */

const API_BASE = import.meta.env?.VITE_API_BASE || "http://localhost:8000";

const STAGES = {
  UPLOAD: "upload",
  ROLE: "role",
  GENERATING: "generating",
  INTERVIEW: "interview",
  SCORING: "scoring",
  SUMMARY: "summary",
};

export default function App() {
  const [stage, setStage] = useState(STAGES.UPLOAD);
  const [error, setError] = useState(null);

  const [resumeFile, setResumeFile] = useState(null);
  const [resumeProfile, setResumeProfile] = useState(null);
  const [targetRole, setTargetRole] = useState("");

  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // question_id -> answer text

  const [summary, setSummary] = useState(null);

  const resetAll = () => {
    setStage(STAGES.UPLOAD);
    setError(null);
    setResumeFile(null);
    setResumeProfile(null);
    setTargetRole("");
    setQuestions([]);
    setCurrentIndex(0);
    setAnswers({});
    setSummary(null);
  };

  const handleResumeUpload = useCallback(async (file) => {
    setError(null);
    setResumeFile(file);
    setStage(STAGES.ROLE);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/parse-resume`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to parse resume.");
      }
      const profile = await res.json();
      setResumeProfile(profile);
    } catch (e) {
      setError(e.message);
      setStage(STAGES.UPLOAD);
    }
  }, []);

  const handleGenerateQuestions = useCallback(async () => {
    if (!resumeProfile || !targetRole.trim()) return;
    setError(null);
    setStage(STAGES.GENERATING);

    try {
      const res = await fetch(`${API_BASE}/api/generate-questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_profile: resumeProfile,
          target_role: targetRole.trim(),
          num_questions: 6,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to generate questions.");
      }
      const data = await res.json();
      setQuestions(data.questions);
      setCurrentIndex(0);
      setStage(STAGES.INTERVIEW);
    } catch (e) {
      setError(e.message);
      setStage(STAGES.ROLE);
    }
  }, [resumeProfile, targetRole]);

  const handleAnswerChange = (questionId, text) => {
    setAnswers((prev) => ({ ...prev, [questionId]: text }));
  };

  const goNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((i) => i + 1);
    } else {
      submitForFeedback();
    }
  };

  const goPrev = () => {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1);
  };

  const submitForFeedback = useCallback(async () => {
    setError(null);
    setStage(STAGES.SCORING);

    const payload = {
      target_role: targetRole.trim(),
      answers: questions.map((q) => ({
        question_id: q.id,
        question_text: q.question,
        question_type: q.type,
        focus_area: q.focus_area,
        answer_text: answers[q.id] || "",
      })),
    };

    try {
      const res = await fetch(`${API_BASE}/api/submit-answers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to score answers.");
      }
      const data = await res.json();
      setSummary(data);
      setStage(STAGES.SUMMARY);
    } catch (e) {
      setError(e.message);
      setStage(STAGES.INTERVIEW);
    }
  }, [questions, answers, targetRole]);

  return (
    <div className="app-root">
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {stage === STAGES.UPLOAD && <UploadStage onUpload={handleResumeUpload} />}

      {stage === STAGES.ROLE && (
        <RoleStage
          resumeFile={resumeFile}
          resumeProfile={resumeProfile}
          targetRole={targetRole}
          onTargetRoleChange={setTargetRole}
          onContinue={handleGenerateQuestions}
          ready={!!resumeProfile}
        />
      )}

      {stage === STAGES.GENERATING && (
        <LoadingStage message="Reading your background and drafting questions for this role…" />
      )}

      {stage === STAGES.INTERVIEW && questions.length > 0 && (
        <InterviewStage
          question={questions[currentIndex]}
          index={currentIndex}
          total={questions.length}
          answer={answers[questions[currentIndex].id] || ""}
          onAnswerChange={(text) => handleAnswerChange(questions[currentIndex].id, text)}
          onNext={goNext}
          onPrev={goPrev}
        />
      )}

      {stage === STAGES.SCORING && (
        <LoadingStage message="Scoring your answers against the role's expectations…" />
      )}

      {stage === STAGES.SUMMARY && summary && (
        <SummaryStage summary={summary} questions={questions} answers={answers} onRestart={resetAll} />
      )}
    </div>
  );
}

/* ----------------------------- Stage 1: Upload ----------------------------- */

function UploadStage({ onUpload }) {
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (file) => {
    if (file && file.type === "application/pdf") {
      onUpload(file);
    }
  };

  return (
    <div className="stage upload-stage">
      <div className="eyebrow">Mock Interview</div>
      <h1>Bring your résumé.<br />We'll do the rest.</h1>
      <p className="lede">
        Upload a résumé and tell us the role you're aiming for. You'll get questions
        built for that exact gap — then real feedback on how you answered, not just
        encouragement.
      </p>

      <label
        className={`dropzone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files[0]);
        }}
      >
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => handleFile(e.target.files[0])}
          hidden
        />
        <span className="dropzone-title">Drop your résumé PDF here</span>
        <span className="dropzone-sub">or click to browse — PDF only, up to 5MB</span>
      </label>
    </div>
  );
}

/* ------------------------------ Stage 2: Role ------------------------------ */

function RoleStage({ resumeProfile, targetRole, onTargetRoleChange, onContinue, ready }) {
  return (
    <div className="stage role-stage">
      <div className="eyebrow">Step 2 of 3</div>
      <h1>What role are you preparing for?</h1>

      {ready ? (
        <div className="profile-card">
          <div className="profile-card-label">From your résumé</div>
          <div className="profile-row">
            <strong>{resumeProfile.current_or_last_title || "Role not detected"}</strong>
            {resumeProfile.years_experience != null && (
              <span className="muted"> · {resumeProfile.years_experience} yrs experience</span>
            )}
          </div>
          {resumeProfile.skills?.length > 0 && (
            <div className="chip-row">
              {resumeProfile.skills.slice(0, 8).map((s) => (
                <span className="chip" key={s}>
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="profile-card profile-card-loading">Reading résumé…</div>
      )}

      <input
        type="text"
        className="role-input"
        placeholder="e.g. Senior Backend Engineer"
        value={targetRole}
        onChange={(e) => onTargetRoleChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && ready && targetRole.trim()) onContinue();
        }}
      />

      <button
        className="primary-btn"
        disabled={!ready || !targetRole.trim()}
        onClick={onContinue}
      >
        Generate my questions
      </button>
    </div>
  );
}

/* --------------------------- Loading interstitial --------------------------- */

function LoadingStage({ message }) {
  return (
    <div className="stage loading-stage">
      <div className="pulse-mark" />
      <p>{message}</p>
    </div>
  );
}

/* --------------------------- Stage 3: Interview --------------------------- */

function InterviewStage({ question, index, total, answer, onAnswerChange, onNext, onPrev }) {
  const progressPct = ((index + 1) / total) * 100;
  const isLast = index === total - 1;

  return (
    <div className="stage interview-stage">
      <div className="progress-rule">
        <div className="progress-fill" style={{ width: `${progressPct}%` }} />
      </div>
      <div className="question-meta">
        <span className={`type-badge type-${question.type}`}>{question.type}</span>
        <span className="focus-tag">{question.focus_area}</span>
        <span className="question-count">
          {index + 1} / {total}
        </span>
      </div>

      <h2 className="question-text">{question.question}</h2>

      <textarea
        className="answer-box"
        placeholder="Type your answer here…"
        value={answer}
        onChange={(e) => onAnswerChange(e.target.value)}
        rows={10}
        autoFocus
      />

      <div className="nav-row">
        <button className="ghost-btn" onClick={onPrev} disabled={index === 0}>
          Back
        </button>
        <button className="primary-btn" onClick={onNext}>
          {isLast ? "Finish & get feedback" : "Next question"}
        </button>
      </div>
    </div>
  );
}

/* ---------------------------- Stage 4: Summary ---------------------------- */

function SummaryStage({ summary, questions, answers, onRestart }) {
  const questionById = Object.fromEntries(questions.map((q) => [q.id, q]));

  return (
    <div className="stage summary-stage">
      <div className="eyebrow">Results · {summary.target_role}</div>
      <h1>Here's how you did.</h1>

      <div className="overall-score-block">
        <span className="overall-score-number">{summary.overall_score.toFixed(1)}</span>
        <span className="overall-score-label">out of 10, overall</span>
      </div>

      {Object.keys(summary.competency_breakdown).length > 0 && (
        <div className="competency-block">
          <div className="block-label">By competency</div>
          {Object.entries(summary.competency_breakdown).map(([area, score]) => (
            <div className="competency-row" key={area}>
              <span className="competency-name">{area}</span>
              <div className="competency-bar-track">
                <div
                  className="competency-bar-fill"
                  style={{ width: `${(score / 10) * 100}%` }}
                />
              </div>
              <span className="competency-score">{score.toFixed(1)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="two-col">
        <div className="summary-list-block strengths">
          <div className="block-label">Top strengths</div>
          <ul>
            {summary.top_strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
        <div className="summary-list-block improvements">
          <div className="block-label">Priority improvements</div>
          <ul>
            {summary.priority_improvements.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="per-question-block">
        <div className="block-label">Question by question</div>
        {summary.per_question_feedback.map((fb) => {
          const q = questionById[fb.question_id];
          return (
            <details className="question-feedback-card" key={fb.question_id}>
              <summary>
                <span className="qf-question">{q?.question || "Question"}</span>
                <span className="qf-score">{fb.score}/10</span>
              </summary>
              <div className="qf-body">
                <p className="qf-your-answer">
                  <strong>Your answer:</strong> {answers[fb.question_id] || "(no answer given)"}
                </p>
                <div className="qf-subscores">
                  <span>Clarity {fb.clarity_score}/10</span>
                  <span>Relevance {fb.relevance_score}/10</span>
                  <span>Depth {fb.depth_score}/10</span>
                </div>
                {fb.strengths.length > 0 && (
                  <div className="qf-strengths">
                    <strong>Strengths:</strong> {fb.strengths.join(" · ")}
                  </div>
                )}
                {fb.gaps.length > 0 && (
                  <div className="qf-gaps">
                    <strong>Gaps:</strong> {fb.gaps.join(" · ")}
                  </div>
                )}
                <div className="qf-tip">
                  <strong>Tip:</strong> {fb.improved_answer_tip}
                </div>
              </div>
            </details>
          );
        })}
      </div>

      <button className="primary-btn" onClick={onRestart}>
        Start a new mock interview
      </button>
    </div>
  );
}
