"""
Question generation: ResumeProfile + target_role -> structured QuestionSet.
"""

import uuid

from app.schemas import ResumeProfile, QuestionSet, InterviewQuestion, QuestionType
from app.llm_client import call_llm_structured


QUESTION_GEN_PROMPT = """You are an expert technical interviewer preparing a mock interview.

CANDIDATE PROFILE:
- Current/last title: {title}
- Years of experience: {years_exp}
- Skills: {skills}
- Tools/technologies: {tools}
- Past roles: {past_roles}

TARGET ROLE: {target_role}

Generate exactly {num_questions} interview questions tailored to this candidate and target role.
Mix behavioral and technical questions (roughly balanced, but weighted toward technical if the
candidate has strong listed skills relevant to the target role). Vary difficulty. Questions should
probe gaps between the candidate's current profile and what the target role likely requires.

For each question, provide a brief internal rationale explaining why you chose it for this
specific candidate (this will be shown to the user as a tooltip, so keep it one sentence).

Return ONLY valid JSON matching this exact schema, nothing else:
{{
  "questions": [
    {{
      "type": "behavioral" or "technical",
      "question": string,
      "focus_area": string,
      "difficulty": "easy" or "medium" or "hard",
      "rationale": string
    }}
  ]
}}"""


async def generate_questions(
    profile: ResumeProfile, target_role: str, num_questions: int = 6
) -> QuestionSet:
    prompt = QUESTION_GEN_PROMPT.format(
        title=profile.current_or_last_title or "Not specified",
        years_exp=profile.years_experience or "Not specified",
        skills=", ".join(profile.skills) or "Not specified",
        tools=", ".join(profile.tools_and_technologies) or "Not specified",
        past_roles="; ".join(profile.past_roles) or "Not specified",
        target_role=target_role,
        num_questions=num_questions,
    )

    structured = await call_llm_structured(prompt, temperature=0.6)

    questions: list[InterviewQuestion] = []
    for q in structured.get("questions", []):
        try:
            questions.append(
                InterviewQuestion(
                    id=str(uuid.uuid4())[:8],
                    type=QuestionType(q["type"]),
                    question=q["question"],
                    focus_area=q.get("focus_area", "General"),
                    difficulty=q.get("difficulty", "medium"),
                    rationale=q.get("rationale", ""),
                )
            )
        except (KeyError, ValueError):
            # Skip any malformed individual question rather than failing the whole batch
            continue

    if not questions:
        raise ValueError("LLM failed to generate any valid questions.")

    return QuestionSet(target_role=target_role, questions=questions)
