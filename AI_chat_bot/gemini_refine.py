"""Optional refinement step: turn raw retrieved snippets into a fluent
answer using the Gemini API. Falls back gracefully if no key is set or
the call fails.
"""

from __future__ import annotations

from typing import Any

SYSTEM_INSTRUCTION = (
    "You are a helpful bilingual assistant that answers in Bangla or English, "
    "matching the language the user asked in (if the user mixes both, prefer "
    "Bangla). Answer ONLY using the provided context snippets from the "
    "knowledge base. If the context does not contain the answer, say so "
    "politely in the user's language instead of making things up. Keep "
    "answers concise and natural, not a list dump of the raw snippets."
)


def build_prompt(question: str, context_entries: list[tuple[dict[str, Any], float]]) -> str:
    context_block = "\n\n".join(
        f"[{entry.get('title', 'Untitled')}]\n{entry.get('content', '')}"
        for entry, _score in context_entries
    )
    if not context_block:
        context_block = "(no relevant context found in the knowledge base)"
    return (
        f"Context:\n{context_block}\n\n"
        f"User question: {question}\n\n"
        "Answer the user's question using the context above."
    )


def refine_answer(api_key: str, question: str, context_entries: list[tuple[dict[str, Any], float]], model_name: str = "gemini-2.0-flash") -> str:
    """Call Gemini to produce a fluent answer. Raises on failure so the
    caller can decide how to fall back."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name, system_instruction=SYSTEM_INSTRUCTION)
    prompt = build_prompt(question, context_entries)
    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Empty response from Gemini")
    return text
