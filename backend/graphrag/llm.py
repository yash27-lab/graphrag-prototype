"""Gemini access: entity extraction and answer synthesis.

All upstream failures are translated into ``LLMError`` so the API layer can
return an accurate HTTP status instead of a generic 500.
"""

import json
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

EXTRACTION_PROMPT = """\
Extract key entities and their relationships from the following text.
Return the result strictly as a JSON object with this structure:
{{
    "entities": [
        {{"id": "entity_name", "type": "Person/Organization/Concept", "description": "brief description"}}
    ],
    "relationships": [
        {{"source": "entity1", "target": "entity2", "relationship": "relationship_type", "description": "brief description"}}
    ]
}}
Text: {text}
"""

SYNTHESIS_PROMPT = """\
Answer the user's query based ONLY on the provided Knowledge Graph context.

Context:
{context}

User Query: {query}
"""


class LLMError(Exception):
    """An upstream LLM call failed; carries the HTTP status to report."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class GeminiService:
    """Thin wrapper around the google-genai client.

    A per-request API key (sent by the frontend settings UI) takes precedence
    over the key configured in the server environment.
    """

    def __init__(self, default_api_key: Optional[str] = None) -> None:
        self._default_api_key = default_api_key

    def extract_graph(
        self, text: str, model: str, api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        raw = self._generate(
            model=model,
            contents=EXTRACTION_PROMPT.format(text=text),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
            api_key=api_key,
        )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError(502, "The model returned malformed JSON during extraction.") from exc
        if not isinstance(data, dict):
            raise LLMError(502, "The model returned an unexpected structure during extraction.")
        return data

    def synthesize_answer(
        self, query: str, context: str, model: str, api_key: Optional[str] = None
    ) -> str:
        return self._generate(
            model=model,
            contents=SYNTHESIS_PROMPT.format(context=context, query=query),
            api_key=api_key,
        )

    def _client(self, api_key: Optional[str]) -> genai.Client:
        key = api_key or self._default_api_key
        try:
            if key:
                return genai.Client(api_key=key)
            return genai.Client()
        except Exception as exc:
            raise LLMError(
                401,
                "No Gemini API key configured. Provide one in the settings UI "
                "or set GEMINI_API_KEY on the backend.",
            ) from exc

    def _generate(
        self,
        model: str,
        contents: str,
        config: Optional[types.GenerateContentConfig] = None,
        api_key: Optional[str] = None,
    ) -> str:
        client = self._client(api_key)
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except Exception as exc:
            raise _translate_error(exc) from exc
        return response.text or ""


def _translate_error(exc: Exception) -> LLMError:
    message = str(exc)
    if "RESOURCE_EXHAUSTED" in message or "429" in message:
        return LLMError(
            429,
            "Gemini API rate limit reached. Wait a moment or switch to a model "
            "with a higher free-tier quota (gemini-2.5-flash).",
        )
    if "UNAUTHENTICATED" in message or "PERMISSION_DENIED" in message or "API key" in message:
        return LLMError(
            401,
            "Gemini rejected the API key. Check the key in settings or the "
            "GEMINI_API_KEY environment variable.",
        )
    return LLMError(502, f"Upstream LLM call failed: {message}")
