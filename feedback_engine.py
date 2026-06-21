"""
Feedback engine: AnswerSubmission(s) -> structured AnswerFeedback + InterviewSummary.

Feedback is generated in a single batched LLM call (all answers at once) rather than
one call per answer. This cuts latency/cost roughly N-fold and lets the model compare
answers against each other for the summary, at the cost of slightly less depth per
individual answer. Worth revisiting as a tunable if per-answer depth becomes the priority.
"""

from app.schemas import AnswerSubmission, AnswerFeedback, InterviewSummary
from app.llm_client import call_llm_structured


FEEDBACK_PROMPT = """You are an expert interview coach reviewing a candidate's mock interview
for the role: {target_role}.

Below are the questions asked and the candidate's answers. For EACH answer, score it and give
specific, actionable feedback. Be honest and rigorous — vague praise is not useful to the
candidate. A generic, non-specific answer should score low on depth even if well-phrased.

QUESTIONS AND ANSWERS:
{qa_block}

For each answer, score 1-10 on: overall, clarity, relevance, depth.
List up to 4 strengths and up to 4 gaps, as short phrases.
Give exactly one concrete, actionable tip for improvement (not a full rewritten answer).

Then provide an overall summary: overall_score (1-10 average), competency_breakdown (map of
focus_area -> average score across questions in that area), top_strengths (up to 5, across the
whole interview), and priority_improvements (up to 5, ranked by importance).

Return ONLY valid JSON matching this exact schema, nothing else:
{{
  "per_question_feedback": [
    {{
      "question_id": string,
      "score": int,
      "clarity_score": int,
      "relevance_score": int,
      "depth_score": int,
      "strengths": [string],
      "gaps": [string],
      "improved_answer_tip": string
    }}
  ],
  "overall_score": number,
  "competency_breakdown": {{"focus_area_name": number}},
  "top_strengths": [string],
  "priority_improvements": [string]
}}"""


def _build_qa_block(answers: list[AnswerSubmission]) -> str:
    lines = []
    for a in answers:
        lines.append(
            f"[question_id: {a.question_id}] ({a.question_type.value}, focus: {a.focus_area})\n"
            f"Q: {a.question_text}\n"
            f"A: {a.answer_text}\n"
        )
    return "\n".join(lines)


async def generate_feedback(
    target_role: str, answers: list[AnswerSubmission]
) -> InterviewSummary:
    if not answers:
        raise ValueError("No answers submitted to score.")

    qa_block = _build_qa_block(answers)
    prompt = FEEDBACK_PROMPT.format(target_role=target_role, qa_block=qa_block)

    structured = await call_llm_structured(prompt, temperature=0.3)

    per_question = []
    for f in structured.get("per_question_feedback", []):
        try:
            per_question.append(AnswerFeedback(**f))
        except Exception:
            continue

    summary = InterviewSummary(
        target_role=target_role,
        overall_score=structured.get("overall_score", 0),
        competency_breakdown=structured.get("competency_breakdown", {}),
        top_strengths=structured.get("top_strengths", []),
        priority_improvements=structured.get("priority_improvements", []),
        per_question_feedback=per_question,
    )
    return summary
