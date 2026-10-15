"""
Gemini API client with Google Search grounding for the AI Answer Agent.

Uses google.genai.Client (API key mode, no Vertex AI).
Returns (text, sources) or raises GeminiError.
"""
from google import genai
from google.genai import types
from loguru import logger


class GeminiError(Exception):
    """Raised on any Gemini failure: bad key, quota, timeout, empty response."""
    pass


def generate_grounded(api_key: str, model: str, prompt: str, timeout_s: float):
    """
    Call Gemini with Google Search grounding.

    Args:
        api_key:   GEMINI_API_KEY value
        model:     model identifier, e.g. 'gemini-2.5-flash'
        prompt:    the full prompt string
        timeout_s: timeout in seconds

    Returns:
        (text, sources) where sources is a list of {'url': ..., 'title': ...}

    Raises:
        GeminiError on any failure
    """
    if not api_key:
        raise GeminiError('GEMINI_API_KEY not set')
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception as exc:
        raise GeminiError(f'{type(exc).__name__}: {exc}') from exc

    text = (resp.text or '').strip()
    if not text:
        raise GeminiError('empty response')

    # Extract grounding URLs (bonus; failure here is not a Gemini failure)
    sources = []
    try:
        for chunk in resp.candidates[0].grounding_metadata.grounding_chunks or []:
            if chunk.web:
                sources.append({
                    'url': chunk.web.uri,
                    'title': chunk.web.title or chunk.web.uri,
                })
    except Exception:
        pass

    return text, sources
