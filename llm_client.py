"""
LLM client: thin wrapper around the Gemini API that enforces structured JSON output.

This is the core "engineering" piece referenced in the brief — every call here
forces response_mime_type="application/json" so the model cannot return prose,
and includes a single repair-retry if parsing fails.
"""

import json
import os
from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.5-flash"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Get a key at https://aistudio.google.com/apikey and export it."
            )
        _client = genai.Client(api_key=api_key)
    return _client


async def call_llm_structured(prompt: str, temperature: float = 0.4) -> dict:
    """
    Call the LLM and force a JSON object response.
    Raises ValueError if the model fails to return parseable JSON after one repair attempt.
    """
    client = _get_client()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )

    raw = (response.text or "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # One repair attempt: ask the model to fix its own malformed output
        repair_prompt = (
            "The following text was supposed to be valid JSON but failed to parse. "
            "Return ONLY the corrected, valid JSON object — no explanation, no markdown fences.\n\n"
            f"{raw}"
        )
        repair_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=repair_prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        repaired_raw = (repair_response.text or "").strip()
        try:
            return json.loads(repaired_raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned unparseable JSON twice: {repaired_raw[:500]}") from e
